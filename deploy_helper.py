#!/usr/bin/env python
"""
Quick deployment helper script
Generates a new SECRET_KEY and shows deployment commands
"""

from django.core.management.utils import get_random_secret_key

print("=" * 60)
print("🚀 DEPLOYMENT HELPER")
print("=" * 60)
print()

# Generate new secret key
secret_key = get_random_secret_key()
print("📝 New SECRET_KEY generated:")
print(f"   {secret_key}")
print()

print("=" * 60)
print("🏆 RECOMMENDED: Deploy to Railway")
print("=" * 60)
print()
print("1. Install Railway CLI:")
print("   npm install -g @railway/cli")
print()
print("2. Login to Railway:")
print("   railway login")
print()
print("3. Initialize project:")
print("   railway init")
print()
print("4. Deploy:")
print("   railway up")
print()
print("5. Add PostgreSQL database in Railway dashboard:")
print("   New → Database → PostgreSQL")
print()
print("6. Set environment variables in Railway dashboard:")
print(f"   SECRET_KEY={secret_key}")
print("   DEBUG=False")
print("   ALLOWED_HOSTS=.railway.app")
print("   CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com")
print("   CSRF_TRUSTED_ORIGINS=https://your-frontend-domain.com")
print()
print("7. Create superuser:")
print("   railway run python manage.py createsuperuser")
print()
print("=" * 60)
print("✅ Your backend will be live at: https://your-app.railway.app")
print("=" * 60)
