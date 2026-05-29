import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# TEMP DIAGNOSTIC: always expose an ASGI `app`. On import failure, `app`
# becomes a tiny ASGI responder that returns the real traceback as text.
try:
    from app.main import app
except Exception:
    _tb = traceback.format_exc()

    async def app(scope, receive, send):
        if scope["type"] != "http":
            return
        await send({
            "type": "http.response.start",
            "status": 500,
            "headers": [(b"content-type", b"text/plain; charset=utf-8")],
        })
        await send({
            "type": "http.response.body",
            "body": ("IMPORT ERROR:\n\n" + _tb).encode("utf-8"),
        })

# Best-effort Lambda handler; never let its import crash the module.
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except Exception:
    pass
