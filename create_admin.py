import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') # Change 'core' to your app name if different
django.setup()

User = get_user_model()
username = 'admin'
email = 'admin@example.com'
password = 'YourSafePassword123' # Change this!

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f"Superuser {username} created successfully!")
else:
    print(f"Superuser {username} already exists.")