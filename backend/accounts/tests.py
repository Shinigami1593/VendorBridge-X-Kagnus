from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from activity.models import ActivityLog


class RegistrationActivityTests(APITestCase):
    def test_registration_is_logged_but_login_is_not(self):
        response = self.client.post('/api/auth/register/', {
            'email': 'new@example.com',
            'password': 'password123',
            'role': 'vendor',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        event = ActivityLog.objects.get(action='user_registered')
        self.assertEqual(event.actor_id, response.data['user']['id'])
        self.assertEqual(event.category, 'auth')
        self.assertEqual(event.object_type, 'user')

        User = get_user_model()
        user = User.objects.get(email='new@example.com')
        self.client.post('/api/auth/login/', {
            'email': user.email, 'password': 'password123',
        }, format='json')
        self.assertEqual(ActivityLog.objects.count(), 1)
