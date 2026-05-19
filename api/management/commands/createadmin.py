from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
import os


class Command(BaseCommand):
    help = "Create or update admin user"

    def handle(self, *args, **kwargs):
        User = get_user_model()

        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "Admin123!")

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "password": make_password(password),
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )

        if not created:
            user.email = email
            user.password = make_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()

        self.stdout.write(
            self.style.SUCCESS(f"Admin user '{username}' ready.")
        )
