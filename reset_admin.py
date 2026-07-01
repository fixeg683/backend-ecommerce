import os
import django

# Initialize Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') # Change 'core' to your main project folder name if different
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
username = 'admin'
password = 'otana4321!' # Change this to your desired secure password

try:
    user = User.objects.get(username=username)
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print(f"Successfully updated password for existing user: {username}")
except User.DoesNotExist:
    User.objects.create_superuser(username=username, email='admin@example.com', password=password)
    print(f"Successfully created brand new superuser: {username}")