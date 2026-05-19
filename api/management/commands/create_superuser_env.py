"""
Management command: create_superuser_env

Reads DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL and
DJANGO_SUPERUSER_PASSWORD from environment variables and creates
(or updates) a superuser — safe to run on every deploy.
"""
import os
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or update a superuser from environment variables"

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin").strip()
        email    = os.environ.get("DJANGO_SUPERUSER_EMAIL",    "admin@example.com").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "StrongPassword123").strip()

        if not password:
            self.stderr.write(
                "⚠️  DJANGO_SUPERUSER_PASSWORD is not set — skipping superuser creation."
            )
            return

        user, created = User.objects.get_or_create(username=username)
        user.email        = email
        user.is_staff     = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(f"✅  {action} superuser: {username}")