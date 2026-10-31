from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APITestCase

from vendors.models import Vendor
from .models import Quotation, RFQ, RFQItem


User = get_user_model()


class RFQTests(APITestCase):
    def setUp(self):
        self.officer = self.user('officer', 'officer@example.com')
        self.manager = self.user('manager', 'manager@example.com')
        self.vendor_user = self.user('vendor', 'one@example.com')
        self.other_user = self.user('vendor', 'two@example.com')
        self.admin = self.user('admin', 'admin@example.com')
        self.vendor = self.make_vendor('one@example.com')
        self.other_vendor = self.make_vendor('two@example.com')

    def user(self, role, email):
        return User.objects.create_user(
            email=email,
            username=email.split('@')[0],
            password='password123',
            role=role,
        )

    def make_vendor(self, email, status='active'):
        index = Vendor.objects.count() + 1
        return Vendor.objects.create(
            name=f'Vendor {index}',
            category='Office',
            gst_number=f'GST{index:012d}',
            contact_person='Contact',
            contact_email=email,
            contact_phone='1234567890',
            status=status,
        )

    def rfq_data(self, vendors=None, items=None, **extra):
        return {
            'title': 'Office supplies',
            'category': 'Office',
            'description': 'Annual purchase',
            'deadline': (timezone.now() + timedelta(days=5)).isoformat(),
            'vendors': vendors if vendors is not None else [self.vendor.pk],
            'items': items if items is not None else [
                {'name': 'Paper', 'quantity': 2, 'unit': 'BOX'},
                {'name': 'Pens', 'quantity': 3, 'unit': 'PACK'},
            ],
            **extra,
        }

    def create_rfq(self, *, vendors=None, items=None, status='open', **extra):
        values = {
            'title': 'Office supplies',
            'category': 'Office',
            'description': '',
            'deadline': timezone.now() + timedelta(days=5),
            'status': status,
            'created_by': self.officer,
        }
        values.update(extra)
        rfq = RFQ.objects.create(**values)
        rfq.vendors.set(vendors if vendors is not None else [self.vendor])
        if items is None:
            items = [
                {'name': 'Paper', 'quantity': 2, 'unit': 'BOX'},
                {'name': 'Pens', 'quantity': 3, 'unit': 'PACK'},
            ]
        RFQItem.objects.bulk_create([RFQItem(rfq=rfq, **item) for item in items])
        return rfq

    def set_user(self, user):
        self.client.force_authenticate(user=user)

    def quote(self, user, rfq, prices, *, submit=True, items=None):
        self.set_user(user)
        if items is None:
            items = [
                {
                    'rfq_item': item.pk,
                    'unit_price': str(price),
                    'delivery_days': days,
                }
                for (item, price, days) in zip(
                    rfq.items.all(), prices, [4] * len(prices)
                )
            ]
        return self.client.put(
            f'/api/rfqs/{rfq.pk}/my-quotation/',
            {
                'tax_percent': '18',
                'payment_terms': 'Net 30',
                'notes': 'Standard offer',
                'submit': submit,
                'items': items,
            },
            format='json',
        )

    def test_officer_creates_rfq_with_items_and_unique_number(self):
        self.set_user(self.officer)
        first = self.client.post('/api/rfqs/', self.rfq_data(), format='json')
        second = self.client.post('/api/rfqs/', self.rfq_data(), format='json')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertTrue(first.data['rfq_number'].startswith('RFQ-'))
        self.assertNotEqual(first.data['rfq_number'], second.data['rfq_number'])
        self.assertEqual(len(first.data['items']), 2)

    def test_manager_and_vendor_cannot_create_rfq(self):
        for user in (self.manager, self.vendor_user):
            self.set_user(user)
            response = self.client.post(
                '/api/rfqs/', self.rfq_data(), format='json'
            )
            self.assertEqual(response.status_code, 403)

    def test_rfq_endpoints_require_authentication(self):
        response = self.client.get('/api/rfqs/')
        self.assertEqual(response.status_code, 401)

    def test_vendor_sees_only_assigned_non_draft_rfqs(self):
        assigned = self.create_rfq()
        not_assigned = self.create_rfq(vendors=[self.other_vendor])
        draft = self.create_rfq(status='draft')
        self.set_user(self.vendor_user)
        response = self.client.get('/api/rfqs/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['id'] for row in response.data], [assigned.pk])
        self.assertEqual(
            self.client.get(f'/api/rfqs/{not_assigned.pk}/').status_code, 404
        )
        self.assertEqual(
            self.client.get(f'/api/rfqs/{draft.pk}/').status_code, 404
        )

    def test_manager_sees_non_draft_rfqs_and_overdue_display_is_closed(self):
        open_rfq = self.create_rfq()
        draft = self.create_rfq(status='draft')
        expired = self.create_rfq(
            deadline=timezone.now() - timedelta(seconds=1)
        )
        self.set_user(self.manager)
        response = self.client.get('/api/rfqs/')
        self.assertEqual(
            {row['id'] for row in response.data},
            {open_rfq.pk, expired.pk},
        )
        self.set_user(self.officer)
        response = self.client.get(f'/api/rfqs/{expired.pk}/')
        self.assertEqual(response.data['status'], 'open')
        self.assertEqual(response.data['display_status'], 'closed')

    def test_items_can_only_be_replaced_on_draft_rfqs(self):
        rfq = self.create_rfq(status='draft')
        self.set_user(self.officer)
        response = self.client.patch(
            f'/api/rfqs/{rfq.pk}/',
            {'items': [{'name': 'New item', 'quantity': 1}]},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(rfq.items.count(), 1)
        rfq.refresh_from_db()
        self.assertEqual(
            list(rfq.items.values_list('name', flat=True)), ['New item']
        )
        rfq.status = 'open'
        rfq.save(update_fields=['status'])
        response = self.client.patch(
            f'/api/rfqs/{rfq.pk}/',
            {'items': [{'name': 'Blocked item', 'quantity': 1}]},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_publish_fails_without_items_or_vendors(self):
        rfq = self.create_rfq(status='draft', vendors=[], items=[])
        self.set_user(self.officer)
        response = self.client.post(f'/api/rfqs/{rfq.pk}/publish/')
        self.assertEqual(response.status_code, 400)
        self.assertIn('items', response.data)
        self.assertIn('vendors', response.data)

    def test_publish_opens_valid_rfq_and_rejects_expired_deadline(self):
        rfq = self.create_rfq(status='draft')
        expired = self.create_rfq(
            status='draft',
            deadline=timezone.now() - timedelta(seconds=1),
        )
        self.set_user(self.officer)
        response = self.client.post(f'/api/rfqs/{rfq.pk}/publish/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'open')
        response = self.client.post(f'/api/rfqs/{expired.pk}/publish/')
        self.assertEqual(response.status_code, 400)
        self.assertIn('deadline', response.data)

    def test_rfq_list_status_and_search_filters(self):
        draft = self.create_rfq(status='draft')
        self.create_rfq()
        self.set_user(self.officer)
        response = self.client.get('/api/rfqs/?status=draft')
        self.assertEqual([row['id'] for row in response.data], [draft.pk])
        response = self.client.get(
            f'/api/rfqs/?search={draft.rfq_number[-4:]}'
        )
        self.assertEqual([row['id'] for row in response.data], [draft.pk])

    def test_inactive_vendors_cannot_be_assigned(self):
        for vendor_status in ('blocked', 'pending'):
            inactive = self.make_vendor(
                f'{vendor_status}@example.com', status=vendor_status
            )
            self.set_user(self.officer)
            response = self.client.post(
                '/api/rfqs/',
                self.rfq_data(vendors=[inactive.pk]),
                format='json',
            )
            self.assertEqual(response.status_code, 400)

    def test_vendor_submits_quotation_and_totals_are_calculated(self):
        rfq = self.create_rfq()
        response = self.quote(self.vendor_user, rfq, [10, 5])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'submitted')
        self.assertEqual(Decimal(response.data['subtotal']), Decimal('35.00'))
        self.assertEqual(Decimal(response.data['tax_amount']), Decimal('6.30'))
        self.assertEqual(Decimal(response.data['grand_total']), Decimal('41.30'))

    def test_vendor_cannot_quote_unassigned_rfq(self):
        rfq = self.create_rfq(vendors=[self.other_vendor])
        self.set_user(self.vendor_user)
        response = self.client.put(
            f'/api/rfqs/{rfq.pk}/my-quotation/',
            {'items': [], 'submit': False},
            format='json',
        )
        self.assertEqual(response.status_code, 404)

    def test_quotation_after_deadline_is_rejected(self):
        rfq = self.create_rfq(deadline=timezone.now() - timedelta(seconds=1))
        response = self.quote(self.vendor_user, rfq, [10, 5])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'Deadline has passed')

    def test_vendor_can_edit_submitted_quote_before_deadline(self):
        rfq = self.create_rfq(vendors=[self.vendor, self.other_vendor])
        self.assertEqual(self.quote(self.vendor_user, rfq, [10, 5]).status_code, 201)
        response = self.quote(self.vendor_user, rfq, [20, 5])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Quotation.objects.filter(rfq=rfq).count(), 1)
        self.assertEqual(Decimal(response.data['subtotal']), Decimal('55.00'))

    def test_quote_rejects_item_from_another_rfq(self):
        rfq = self.create_rfq()
        other = self.create_rfq(vendors=[self.vendor])
        item = other.items.first()
        response = self.quote(
            self.vendor_user,
            rfq,
            [],
            items=[{
                'rfq_item': item.pk,
                'unit_price': '3',
                'delivery_days': 1,
            }],
        )
        self.assertEqual(response.status_code, 400)

    def test_submission_requires_every_item_to_be_priced(self):
        rfq = self.create_rfq()
        response = self.quote(self.vendor_user, rfq, [], items=[{
            'rfq_item': rfq.items.first().pk,
            'unit_price': '2',
            'delivery_days': 1,
        }])
        self.assertEqual(response.status_code, 400)
        self.assertIn('items', response.data)

    def test_comparison_lowest_sort_filters_and_empty_results(self):
        rfq = self.create_rfq(vendors=[self.vendor, self.other_vendor])
        self.vendor.rating = Decimal('4.5')
        self.vendor.save(update_fields=['rating'])
        self.other_vendor.rating = Decimal('3.0')
        self.other_vendor.save(update_fields=['rating'])
        self.assertEqual(self.quote(self.vendor_user, rfq, [10, 5]).status_code, 201)
        self.assertEqual(
            self.quote(self.other_user, rfq, [20, 10]).status_code, 201
        )
        self.set_user(self.officer)
        response = self.client.get(f'/api/rfqs/{rfq.pk}/comparison/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['quotations'][0]['vendor_id'], self.vendor.pk
        )
        self.assertEqual(
            [q['is_lowest'] for q in response.data['quotations']],
            [True, False],
        )
        sorted_response = self.client.get(
            f'/api/rfqs/{rfq.pk}/comparison/?sort=delivery&max_delivery=4&min_rating=0'
        )
        self.assertEqual(sorted_response.status_code, 200)
        self.assertEqual(len(sorted_response.data['quotations']), 2)
        no_delivery_match = self.client.get(
            f'/api/rfqs/{rfq.pk}/comparison/?max_delivery=3'
        )
        self.assertEqual(no_delivery_match.data['quotations'], [])
        filtered = self.client.get(
            f'/api/rfqs/{rfq.pk}/comparison/?min_rating=4'
        )
        self.assertEqual(len(filtered.data['quotations']), 1)
        self.assertEqual(
            filtered.data['quotations'][0]['vendor_id'], self.vendor.pk
        )
        rated = self.client.get(f'/api/rfqs/{rfq.pk}/comparison/?sort=rating')
        self.assertEqual(
            [q['vendor_id'] for q in rated.data['quotations']],
            [self.vendor.pk, self.other_vendor.pk],
        )
        empty = self.create_rfq(vendors=[self.vendor])
        response = self.client.get(f'/api/rfqs/{empty.pk}/comparison/')
        self.assertEqual(response.data['quotations'], [])

    def test_vendor_cannot_open_comparison(self):
        rfq = self.create_rfq()
        self.set_user(self.vendor_user)
        response = self.client.get(f'/api/rfqs/{rfq.pk}/comparison/')
        self.assertEqual(response.status_code, 403)

    def test_officer_selects_submitted_quotation_and_rejects_other_rfq_quote(self):
        rfq = self.create_rfq()
        other_rfq = self.create_rfq(vendors=[self.vendor])
        self.assertEqual(self.quote(self.vendor_user, rfq, [10, 5]).status_code, 201)
        self.assertEqual(
            self.quote(self.vendor_user, other_rfq, [10, 5]).status_code, 201
        )
        own_quote = Quotation.objects.get(rfq=rfq)
        other_quote = Quotation.objects.get(rfq=other_rfq)
        self.set_user(self.officer)
        response = self.client.post(
            f'/api/rfqs/{rfq.pk}/select-quotation/',
            {'quotation_id': own_quote.pk},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'selected')
        rfq.status = 'open'
        rfq.save(update_fields=['status'])
        invalid = self.client.post(
            f'/api/rfqs/{rfq.pk}/select-quotation/',
            {'quotation_id': other_quote.pk},
            format='json',
        )
        self.assertEqual(invalid.status_code, 400)

    def test_vendor_can_get_empty_or_existing_own_quotation(self):
        rfq = self.create_rfq()
        self.set_user(self.vendor_user)
        self.assertEqual(
            self.client.get(f'/api/rfqs/{rfq.pk}/my-quotation/').data, {}
        )
        self.quote(self.vendor_user, rfq, [10, 5])
        response = self.client.get(f'/api/rfqs/{rfq.pk}/my-quotation/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['vendor'], self.vendor.pk)
        rfq_response = self.client.get(f'/api/rfqs/{rfq.pk}/')
        self.assertEqual(rfq_response.data['my_quotation_status'], 'submitted')
        self.assertEqual(len(self.client.get('/api/my-quotations/').data), 1)

    def test_attachment_extension_and_size_are_checked(self):
        rfq = self.create_rfq()
        self.set_user(self.officer)
        bad = SimpleUploadedFile('malware.exe', b'x')
        response = self.client.post(
            f'/api/rfqs/{rfq.pk}/attachments/', {'file': bad}, format='multipart'
        )
        self.assertEqual(response.status_code, 400)
        too_large = SimpleUploadedFile('large.pdf', b'x' * (5 * 1024 * 1024 + 1))
        response = self.client.post(
            f'/api/rfqs/{rfq.pk}/attachments/',
            {'file': too_large},
            format='multipart',
        )
        self.assertEqual(response.status_code, 400)

    def test_officer_can_add_and_remove_attachment(self):
        rfq = self.create_rfq()
        self.set_user(self.officer)
        file = SimpleUploadedFile('quote.pdf', b'pdf data')
        response = self.client.post(
            f'/api/rfqs/{rfq.pk}/attachments/',
            {'file': file},
            format='multipart',
        )
        self.assertEqual(response.status_code, 201)
        attachment_id = response.data['id']
        response = self.client.delete(
            f'/api/rfqs/{rfq.pk}/attachments/{attachment_id}/'
        )
        self.assertEqual(response.status_code, 204)

    def test_rating_is_editable_only_by_officers_and_admins(self):
        self.set_user(self.manager)
        response = self.client.patch(
            f'/api/vendors/{self.vendor.pk}/',
            {'rating': '4.5'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)
        self.set_user(self.officer)
        response = self.client.patch(
            f'/api/vendors/{self.vendor.pk}/',
            {'rating': '4.5'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.data['rating']), Decimal('4.5'))
