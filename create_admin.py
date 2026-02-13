from django.contrib.auth import get_user_model
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'camera_demo_backend.settings')
django.setup()

User = get_user_model()

# Delete existing admin user if exists
User.objects.filter(email='admin@example.com').delete()

# Create new admin user
admin = User.objects.create_superuser(
    username='admin',
    email='admin@example.com',
    password='admin'
)

print('✅ Admin user created successfully!')
print('Email: admin@example.com')
print('Password: admin')
