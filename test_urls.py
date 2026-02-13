import os
import sys
import django
from django.urls import resolve, Resolver404

# Set settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'camera_demo_backend.settings')

print("Starting URL Resolution Diagnostic...")

try:
    django.setup()
    
    test_paths = [
        '/api/proctor/health/',
        '/api/proctor/exams/',
        '/api/proctor/analyze/',
        '/api/proctor/log_violation/',
    ]
    
    print("\n--- Testing Path Resolution ---")
    for path in test_paths:
        try:
            match = resolve(path)
            print(f"✅ MATCH FOUND: {path}")
            print(f"   - View: {match.view_name}")
            print(f"   - Func: {match.func}")
            print(f"   - Args: {match.args}")
            print(f"   - Kwargs: {match.kwargs}")
        except Resolver404:
            print(f"❌ 404 NOT FOUND: {path}")
        except Exception as e:
            print(f"⚠️ ERROR resolving {path}: {e}")
    print("--- End of Resolution Test ---\n")

except Exception as e:
    print(f"Critical initialization error: {e}")
    import traceback
    traceback.print_exc()
