"""Math Service — re-export from current location."""
# Actual code in agent/math_service/app.py
# This shim enables `from app.services.math import app as math_app`
try:
    from math_service.app import app as math_app
except ImportError:
    math_app = None
