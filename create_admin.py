import os
import django

# 1. Set the settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') 

# 2. Initialize Django (CRITICAL: Do this before importing models)
django.setup()

# 3. Now it is safe to import auth
from django.contrib.auth import get_user_model

def create_admin():
    User = get_user_model()
    username = 'admin'
    email = 'admin@example.com'
    password = 'YourSafePassword123' # Use a strong password

    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username, email, password)
        print(f"Superuser '{username}' created successfully!")
    else:
        print(f"Superuser '{username}' already exists.")

if __name__ == "__main__":
    create_admin()