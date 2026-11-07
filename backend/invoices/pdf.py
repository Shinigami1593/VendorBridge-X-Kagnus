from io import BytesIO

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_invoice_pdf(invoice):
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph('<b>INVOICE</b>', styles['Title']),
        Paragraph(f'Invoice number: {invoice.invoice_number}', styles['Normal']),
        Spacer(1, 8 * mm),
    ]
    po = invoice.purchase_order
    story.append(Table([
        [
            Paragraph(
                f'<b>Bill to</b><br/>{settings.ORG_NAME}<br/>'
                f'{settings.ORG_ADDRESS}<br/>GSTIN: {settings.ORG_GSTIN}',
                styles['Normal'],
            ),
            Paragraph(
                f'<b>Vendor</b><br/>{po.vendor_name}<br/>'
                f'{po.vendor_address}<br/>GSTIN: {po.vendor_gstin}',
                styles['Normal'],
            ),
        ],
    ], colWidths=[85 * mm, 85 * mm]))
    story.extend([
        Spacer(1, 6 * mm),
        Paragraph(
            f'PO number: {po.po_number} &nbsp;&nbsp; '
            f'Invoice date: {invoice.invoice_date} &nbsp;&nbsp; '
            f'Due date: {invoice.due_date}',
            styles['Normal'],
        ),
        Spacer(1, 6 * mm),
    ])
    rows = [['Item', 'Qty', 'Unit', 'Unit price', 'Total']]
    rows.extend([
        [item.name, str(item.quantity), item.unit,
         f'{item.unit_price:.2f}', f'{item.total:.2f}']
        for item in invoice.items.all()
    ])
    table = Table(rows, repeatRows=1, colWidths=[67 * mm, 20 * mm, 20 * mm, 30 * mm, 30 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8edf2')),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.extend([table, Spacer(1, 6 * mm)])
    totals = [
        ['Subtotal', f'{invoice.subtotal:.2f}'],
        [f'CGST ({invoice.cgst_percent}%)', f'{invoice.cgst_amount:.2f}'],
        [f'SGST ({invoice.sgst_percent}%)', f'{invoice.sgst_amount:.2f}'],
        ['Grand total', f'{invoice.grand_total:.2f}'],
        ['Status', invoice.status],
    ]
    summary = Table(totals, colWidths=[130 * mm, 37 * mm], hAlign='RIGHT')
    summary.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('LINEABOVE', (0, -2), (-1, -2), 0.8, colors.black),
    ]))
    story.append(summary)
    document.build(story)
    return buffer.getvalue()
