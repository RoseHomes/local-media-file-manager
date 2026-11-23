import os
import sys
from pathlib import Path

from django.core.asgi import get_asgi_application


BASE_DIR = Path(__file__).resolve().parent.parent
VENDOR_DIR = BASE_DIR / ".vendor"
if VENDOR_DIR.exists():
    sys.path.insert(0, str(VENDOR_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fanart_manager.settings")

application = get_asgi_application()
