import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the real app; capture any failure so we can surface it at runtime.
# NOTE: `app` MUST be defined at module top level — Vercel's Python builder
# statically scans for a top-level `app`/`application`/`handler`.
_real_app = None
_tb = None
try:
    from app.main import app as _real_app
except Exception:
    _tb = traceback.format_exc()


async def app(scope, receive, send):
    if _real_app is not None:
        return await _real_app(scope, receive, send)
    if scope["type"] != "http":
        return
    body = ("IMPORT ERROR:\n\n" + (_tb or "unknown")).encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": 500,
        "headers": [(b"content-type", b"text/plain; charset=utf-8")],
    })
    await send({"type": "http.response.body", "body": body})
