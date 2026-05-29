import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# TEMP DIAGNOSTIC: if importing the app (or mangum) fails, fall back to a
# dependency-free WSGI app that returns the real traceback as plain text.
# Revert to the plain Mangum entrypoint once the cause is fixed.
try:
    from app.main import app as _asgi_app
    from mangum import Mangum
    handler = Mangum(_asgi_app, lifespan="off")
except Exception:
    _tb = traceback.format_exc()

    def app(environ, start_response):
        start_response("500 Internal Server Error",
                       [("Content-Type", "text/plain; charset=utf-8")])
        return [("IMPORT ERROR:\n\n" + _tb).encode("utf-8")]
