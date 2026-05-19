# Fix Django Admin Login Error on Render

Error:

> Please enter the correct username and password for a staff account.

This usually means one of these problems exists in the deployed Render database:

1. No superuser exists
2. The account is not marked as `is_staff=True`
3. The password hash is invalid
4. The database changed after redeploy
5. Environment variables changed and a new database was created

Since Render Shell is unavailable, the safest fix is to auto-create a Django superuser during deployment.

---

# Step 1 — Create Management Command

Create this file:

`api/management/commands/create_superuser.py`

```python
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Create superuser automatically if it does not exist'

    def handle(self, *args, **kwargs):
        User = get_user_model()

        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not username or not password:
            self.stdout.write(self.style.WARNING(
                'Superuser environment variables not set.'
            ))
            return

        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)

            # Ensure admin permissions exist
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save()

            self.stdout.write(self.style.SUCCESS(
                f'Superuser {username} updated successfully.'
            ))
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )

        self.stdout.write(self.style.SUCCESS(
            f'Superuser {username} created successfully.'
        ))
```

---

# Step 2 — Create Required Folders

Ensure these folders and files exist:

```text
api/
 └── management/
      ├── __init__.py
      └── commands/
           ├── __init__.py
           └── create_superuser.py
```

If `__init__.py` files do not exist, create empty ones.

---

# Step 3 — Update build.sh

Update your `build.sh` file.

Replace it with:

```bash
#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
python manage.py create_superuser
```

---

# Step 4 — Add Render Environment Variables

Open Render Dashboard:

`Service → Environment`

Add:

```text
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=StrongPassword123
```

Use your own secure password.

---

# Step 5 — Redeploy Render

After pushing the changes to GitHub:

1. Open Render
2. Select backend service
3. Click “Manual Deploy”
4. Click “Deploy latest commit”

During deployment the logs should show:

```text
Superuser admin created successfully.
```

or:

```text
Superuser admin updated successfully.
```

---

# Step 6 — Login URL

Use:

```text
https://your-render-url.onrender.com/admin/
```

Login using:

```text
Username: admin
Password: your password
```

---

# Additional Important Check

Verify `core/settings.py` contains:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
```

and verify `core/urls.py` contains:

```python
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
]
```

---

# Why This Fix Works

Your current deployment likely uses a fresh PostgreSQL database where the old admin account does not exist anymore.

Because Render Shell access is unavailable, automatically creating the superuser during deployment guarantees:

* admin account always exists
* password is always reset correctly
* `is_staff=True`
* `is_superuser=True`
* admin login works after every redeploy
