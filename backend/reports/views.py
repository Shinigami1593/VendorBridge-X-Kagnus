import csv
from datetime import date
from decimal import Decimal
from io import StringIO

from django.db.models import Count, Max, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrOfficerOrManager
from activity.utils import log
from approvals.models import Approval
from invoices.models import Invoice
from purchase_orders.models import PurchaseOrder
from rfqs.models import Quotation, RFQ
from vendors.models import Vendor
from .periods import report_period

ZERO = Decimal('0.00')


def money(value):
    return (value or ZERO).quantize(Decimal('0.01'))


def within(queryset, field, start, end):
    return queryset.filter(**{
        f'{field}__date__gte': start,
        f'{field}__date__lte': end,
    })


def build_summary(start, end):
    today = timezone.localdate()
    pos = within(PurchaseOrder.objects.all(), 'created_at', start, end)
    invoices = within(Invoice.objects.all(), 'created_at', start, end)
    rfqs = within(RFQ.objects.all(), 'created_at', start, end)
    approvals = within(Approval.objects.all(), 'created_at', start, end)
    po_total = pos.aggregate(total=Sum('grand_total'))['total']
    po_count = pos.count()
    paid_po_count = pos.filter(invoice__status='paid').count()
    inv_totals = invoices.aggregate(
        invoiced=Sum('grand_total'),
        paid=Sum('grand_total', filter=Q(status='paid')),
        outstanding=Sum('grand_total', filter=Q(status='pending_payment')),
    )
    # RFQs are counted by creation date; quotations by submission date.
    # Approval counts use creation date and are grouped by their current status.
    stats = {
        'rfqs_created': rfqs.count(),
        'rfqs_open': rfqs.filter(status='open').count(),
        'quotations_received': within(
            Quotation.objects.filter(status='submitted'), 'submitted_at',
            start, end,
        ).count(),
        'approvals_pending': approvals.filter(status='pending').count(),
        'approvals_approved': approvals.filter(status='approved').count(),
        'approvals_rejected': approvals.filter(status='rejected').count(),
        'pos_count': po_count,
        'invoices_count': invoices.count(),
        'invoices_paid': invoices.filter(status='paid').count(),
        # Invoice amounts use grand_total for invoices created in the period.
        'amount_invoiced': money(inv_totals['invoiced']),
        'amount_paid': money(inv_totals['paid']),
        'amount_outstanding': money(inv_totals['outstanding']),
    }

    # Category spend is grouped by RFQ category and divided by period PO spend.
    category_rows = pos.values('rfq__category').annotate(
        total=Sum('grand_total')
    ).order_by('rfq__category')
    category_total = money(po_total)
    spend_by_category = [{
        'category': row['rfq__category'],
        'total': money(row['total']),
        'percent': money(
            row['total'] * 100 / category_total if category_total else ZERO
        ),
    } for row in category_rows]
    # Top vendors rank period purchase orders by grand total.
    top_vendors = [{
        'vendor_id': row['vendor_id'],
        'vendor': row['vendor_name'],
        'spend': money(row['spend']),
        'po_count': row['po_count'],
    } for row in pos.values('vendor_id', 'vendor_name').annotate(
        spend=Sum('grand_total'), po_count=Count('id')
    ).order_by('-spend', 'vendor_name')[:5]]

    selected_month = end.replace(day=1)
    month_index = selected_month.year * 12 + selected_month.month - 1
    first_index = month_index - 5
    first_year, first_month_index = divmod(first_index, 12)
    trend_start = date(first_year, first_month_index + 1, 1)
    # Trend includes PO spend/count and RFQ creation counts for the six months.
    trend_pos = PurchaseOrder.objects.filter(
        created_at__date__gte=trend_start,
        created_at__date__lte=end,
    ).annotate(month=TruncMonth('created_at')).values('month').annotate(
        total=Sum('grand_total'), count=Count('id')
    )
    trend_rfqs = RFQ.objects.filter(
        created_at__date__gte=trend_start,
        created_at__date__lte=end,
    ).annotate(month=TruncMonth('created_at')).values('month').annotate(
        count=Count('id')
    )
    po_months = {
        row['month'].strftime('%Y-%m'): row for row in trend_pos
    }
    rfq_months = {
        row['month'].strftime('%Y-%m'): row['count'] for row in trend_rfqs
    }
    monthly_trend = []
    for offset in range(6):
        year, month_index = divmod(first_index + offset, 12)
        month = month_index + 1
        key = f'{year:04d}-{month:02d}'
        row = po_months.get(key, {})
        monthly_trend.append({
            'month': key,
            'label': date(year, month, 1).strftime('%b'),
            'total_spend': money(row.get('total')),
            'po_count': row.get('count', 0),
            'rfq_count': rfq_months.get(key, 0),
        })

    # Invitations count distinct RFQs assigned to each vendor in the period.
    invited = Vendor.objects.filter(
        rfqs__created_at__date__gte=start,
        rfqs__created_at__date__lte=end,
    ).values('id').annotate(count=Count('rfqs', distinct=True))
    # Submitted quotations are counted by submission date.
    submitted = Quotation.objects.filter(
        status='submitted',
        submitted_at__date__gte=start,
        submitted_at__date__lte=end,
    ).values('vendor_id').annotate(count=Count('id'))
    # Selections are counted by RFQs whose selected quotation belongs to vendor.
    selected = Quotation.objects.filter(
        selected_for__created_at__date__gte=start,
        selected_for__created_at__date__lte=end,
    ).values('vendor_id').annotate(count=Count('id'))
    performance_pos = pos.values('vendor_id').annotate(
        count=Count('id'), spend=Sum('grand_total'),
        paid=Count('invoice', filter=Q(invoice__status='paid')),
    )
    # Each quotation's delivery estimate is its slowest quoted line item.
    delivery = Quotation.objects.filter(
        status='submitted',
        submitted_at__date__gte=start,
        submitted_at__date__lte=end,
    ).annotate(max_delivery=Max('items__delivery_days')).values(
        'vendor_id', 'max_delivery'
    )
    invited_map = {r['id']: r['count'] for r in invited}
    submitted_map = {r['vendor_id']: r['count'] for r in submitted}
    selected_map = {r['vendor_id']: r['count'] for r in selected}
    po_map = {r['vendor_id']: r for r in performance_pos}
    delivery_totals = {}
    delivery_counts = {}
    for row in delivery:
        if row['max_delivery'] is not None:
            vendor_id = row['vendor_id']
            delivery_totals[vendor_id] = (
                delivery_totals.get(vendor_id, 0) + row['max_delivery']
            )
            delivery_counts[vendor_id] = delivery_counts.get(vendor_id, 0) + 1
    delivery_map = {
        vendor_id: delivery_totals[vendor_id] / count
        for vendor_id, count in delivery_counts.items()
    }
    vendor_ids = set(invited_map) | set(submitted_map) | set(selected_map) | set(po_map)
    vendor_rows = Vendor.objects.filter(pk__in=vendor_ids).order_by('name')
    vendor_performance = []
    for vendor in vendor_rows:
        invite_count = invited_map.get(vendor.pk, 0)
        submitted_count = submitted_map.get(vendor.pk, 0)
        selection_count = selected_map.get(vendor.pk, 0)
        vendor_po = po_map.get(vendor.pk, {})
        vendor_pos_count = vendor_po.get('count', 0)
        vendor_paid = vendor_po.get('paid', 0)
        vendor_performance.append({
            'vendor_id': vendor.pk,
            'vendor': vendor.name,
            'rating': vendor.rating,
            'rfqs_invited': invite_count,
            'quotations_submitted': submitted_count,
            # Response rate = submitted quotations / RFQs invited.
            'response_rate_percent': money(
                Decimal(submitted_count * 100) / invite_count if invite_count else ZERO
            ),
            'times_selected': selection_count,
            # Win rate = selected quotations / submitted quotations.
            'win_rate_percent': money(
                Decimal(selection_count * 100) / submitted_count
                if submitted_count else ZERO
            ),
            'po_count': vendor_pos_count,
            'spend': money(vendor_po.get('spend')),
            'avg_quoted_delivery_days': (
                round(delivery_map[vendor.pk], 2)
                if delivery_map.get(vendor.pk) is not None else None
            ),
            # Paid invoices are those linked to POs created in the period.
            'paid_invoices': vendor_paid,
            # Fulfillment = paid invoices / POs in the selected period.
            'fulfillment_percent': money(
                Decimal(vendor_paid * 100) / vendor_pos_count
                if vendor_pos_count else ZERO
            ),
        })

    return {
        'cards': {
            # Spend is PO grand total based on PO creation date.
            'total_spend': money(po_total),
            # Active vendor count is current status, independent of period.
            'active_vendors': Vendor.objects.filter(status='active').count(),
            # Fulfillment = POs with a paid invoice / POs created in the period.
            'po_fulfillment_percent': money(
                Decimal(paid_po_count * 100) / po_count if po_count else ZERO
            ),
            # Overdue counts all pending invoices due before today.
            'overdue_invoices': Invoice.objects.filter(
                status='pending_payment', due_date__lt=today
            ).count(),
        },
        'stats': stats,
        'spend_by_category': spend_by_category,
        'top_vendors': top_vendors,
        'monthly_trend': monthly_trend,
        'vendor_performance': vendor_performance,
    }


class ReportSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrOfficerOrManager]

    def get(self, request):
        start, end, label = report_period(request.query_params)
        data = build_summary(start, end)
        return Response({
            'period': {'from': start, 'to': end, 'label': label},
            **data,
        })


def category_export_rows(start, end):
    rows = PurchaseOrder.objects.filter(
        created_at__date__gte=start, created_at__date__lte=end
    )
    total = rows.aggregate(total=Sum('grand_total'))['total'] or ZERO
    return [{
        'category': row['rfq__category'],
        'total': money(row['total']),
        'percent': money(row['total'] * 100 / total if total else ZERO),
    } for row in rows.values('rfq__category').annotate(
        total=Sum('grand_total')
    ).order_by('rfq__category')]


EXPORTS = {
    'spend_by_category': (
        ['category', 'total', 'percent'],
        category_export_rows,
    ),
    'vendors': (
        ['vendor_id', 'vendor', 'status', 'rating'],
        lambda start, end: list(Vendor.objects.values(
            'id', 'name', 'status', 'rating'
        ).order_by('name')),
    ),
    'purchase_orders': (
        ['po_number', 'vendor', 'rfq', 'grand_total', 'status', 'created_at'],
        lambda start, end: list(PurchaseOrder.objects.filter(
            created_at__date__gte=start, created_at__date__lte=end
        ).values('po_number', 'vendor_name', 'rfq__rfq_number', 'grand_total',
                 'status', 'created_at').order_by('created_at')),
    ),
    'invoices': (
        ['invoice_number', 'vendor', 'po_number', 'grand_total', 'status',
         'invoice_date', 'due_date'],
        lambda start, end: list(Invoice.objects.filter(
            created_at__date__gte=start, created_at__date__lte=end
        ).values('invoice_number', 'purchase_order__vendor_name',
                 'purchase_order__po_number', 'grand_total', 'status',
                 'invoice_date', 'due_date').order_by('created_at')),
    ),
}


def safe_cell(value):
    text = '' if value is None else str(value)
    return "'" + text if isinstance(value, str) and text.startswith(
        ('=', '+', '-', '@')
    ) else text


class ReportExportView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrOfficerOrManager]

    def get(self, request):
        export_type = request.query_params.get('type', '')
        if export_type not in EXPORTS:
            raise ValidationError({'type': 'Unsupported report export type.'})
        start, end, _ = report_period(request.query_params)
        headers, get_rows = EXPORTS[export_type]
        rows = get_rows(start, end)
        # Map model field aliases to the stable CSV header names.
        aliases = {
            'vendors': {'vendor_id': 'id', 'vendor': 'name'},
            'purchase_orders': {
                'vendor': 'vendor_name', 'rfq': 'rfq__rfq_number',
            },
            'invoices': {
                'vendor': 'purchase_order__vendor_name',
                'po_number': 'purchase_order__po_number',
            },
        }.get(export_type, {})
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([
                safe_cell(row.get(aliases.get(header, header)))
                for header in headers
            ])
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        month = start.strftime('%Y-%m')
        response['Content-Disposition'] = (
            f'attachment; filename="vendorbridge-{export_type}-{month}.csv"'
        )
        log(
            request.user, 'auth', 'report_exported',
            f'Report exported - {export_type.replace("_", " ")}',
        )
        return response
