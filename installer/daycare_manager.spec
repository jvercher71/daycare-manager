# -*- mode: python ; coding: utf-8 -*-
"""
daycare_manager.spec — PyInstaller build spec for Daycare Manager v2.

Build on Mac:   pyinstaller installer/daycare_manager.spec
Build on Win:   pyinstaller installer\daycare_manager.spec
"""
import sys
import os

block_cipher = None
IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

# Root of the repo (one level up from this spec file)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

a = Analysis(
    [os.path.join(ROOT, "launcher.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[
        # App source package
        (os.path.join(ROOT, "app"),        "app"),
        # Static frontend
        (os.path.join(ROOT, "static"),     "static"),
        # Alembic config for migrations (optional at runtime)
        (os.path.join(ROOT, "alembic.ini"), "."),
        (os.path.join(ROOT, "alembic"),    "alembic"),
        # Icons (used by launcher at runtime)
        (os.path.join(ROOT, "installer", "icon.icns"), "installer"),
        (os.path.join(ROOT, "installer", "icon.ico"),  "installer"),
    ],
    hiddenimports=[
        # FastAPI / Starlette internals
        "uvicorn.lifespan.on",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "email_validator",
        # SQLAlchemy async
        "sqlalchemy.ext.asyncio",
        "aiosqlite",
        "greenlet",
        # jose
        "jose",
        "jose.jwt",
        # bcrypt
        "bcrypt",
        # pydantic
        "pydantic.deprecated.class_validators",
        # mangum (Vercel adapter, safe to include)
        "mangum",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"] if IS_MAC else [],  # Mac uses rumps; Windows keeps tkinter
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DaycareManagerV2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                        # No terminal window
    icon=os.path.join(ROOT, "installer", "icon.icns") if IS_MAC
         else os.path.join(ROOT, "installer", "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DaycareManagerV2",
)

if IS_MAC:
    app = BUNDLE(
        coll,
        name="Daycare Manager v2.app",
        icon=os.path.join(ROOT, "installer", "icon.icns"),
        bundle_identifier="com.daycaremanager.v2",
        info_plist={
            "CFBundleName": "Daycare Manager v2",
            "CFBundleDisplayName": "Daycare Manager v2",
            "CFBundleVersion": "2.0.0",
            "CFBundleShortVersionString": "2.0.0",
            "NSHighResolutionCapable": True,
            "LSUIElement": True,   # Hide from Dock (menu-bar-only app)
        },
    )
