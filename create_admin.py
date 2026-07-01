import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models import Category


class Command(BaseCommand):
    help = "Create or reset admin user and seed default categories"

    def handle(self, *args, **kwargs):
        User = get_user_model()

        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
        email    = os.getenv("DJANGO_SUPERUSER_EMAIL",    "jacobotana96@gmail.com")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "adminpassword")  # Change this to your desired secure password

        user, created = User.objects.get_or_create(username=username)

        # Always reset every field so a stale DB or wrong hash can never block login
        user.email        = email
        user.is_staff     = True
        user.is_superuser = True
        user.is_active    = True
        user.set_password(password)   # ✅ use set_password — handles hashing correctly
        user.save()

        status = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(
            f"[createadmin] Admin user '{username}' {status}. "
            f"Login → /admin/  |  password from DJANGO_SUPERUSER_PASSWORD env var."
        ))

        # Seed default categories
        for cat_name in ["Softwares", "Games", "Movies", "E-book"]:
            _, cat_created = Category.objects.get_or_create(name=cat_name)
            if cat_created:
                self.stdout.write(self.style.SUCCESS(
                    f"[createadmin] Category '{cat_name}' seeded."
                ))