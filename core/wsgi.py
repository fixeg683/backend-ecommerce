import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Vercel expects the callable named `app`
app = get_wsgi_application()

# Gunicorn/Render expects `application`
application = app