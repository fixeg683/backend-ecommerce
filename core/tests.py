from django.contrib.auth import authenticate, get_user_model
from django.test import TestCase


class EmailOrUsernameBackendTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="admin",
            email="admin@example.com",
            password="Admin123!",
            is_staff=True,
            is_superuser=True,
        )

    def test_authenticates_staff_user_by_username(self):
        user = authenticate(username="admin", password="Admin123!")

        self.assertEqual(user, self.user)

    def test_authenticates_staff_user_by_email(self):
        user = authenticate(username="admin@example.com", password="Admin123!")

        self.assertEqual(user, self.user)
