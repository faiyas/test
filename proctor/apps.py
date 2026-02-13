from django.apps import AppConfig

class ProctorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'proctor'

    def ready(self):
        # Pre-load models only in the main worker process, not the reloader wrapper
        import os
        if os.environ.get('RUN_MAIN') == 'true':
            print("="*60)
            print("🚀 PRE-LOADING PROCTORING MODELS...")
            try:
                from proctor.detector import get_object_model
                get_object_model()
                print("✅ OBJECT DETECTION MODEL PRE-LOADED")
                
                from proctor.mobile_phone_detector import MobilePhoneDetector
                MobilePhoneDetector.get_instance()
                print("✅ MOBILE PHONE MODEL PRE-LOADED")
            except Exception as e:
                print(f"⚠️ WARNING: Model pre-loading failed: {e}")
                print("The models will attempt to load again upon the first request.")
            print("="*60)
