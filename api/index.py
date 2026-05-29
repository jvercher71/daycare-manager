import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# TEMP DIAGNOSTIC: surface the real import error instead of an opaque
# FUNCTION_INVOCATION_FAILED. Revert once the cause is identified.
try:
    from app.main import app
except Exception:
    _tb = traceback.format_exc()

    async def app(scope, receive, send):
        if scope["type"] != "http":
            return
        body = ("IMPORT ERROR:\n\n" + _tb).encode()
        await send({
            "type": "http.response.start",
            "status": 500,
            "headers": [(b"content-type", b"text/plain; charset=utf-8")],
        })
        await send({"type": "http.response.body", "body": body})

from mangum import Mangum

handler = Mangum(app, lifespan="off")
