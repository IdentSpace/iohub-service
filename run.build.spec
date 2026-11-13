# -*- mode: python ; coding: utf-8 -*-

import tomllib

from PyInstaller.utils.hooks import copy_metadata
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)


with open('pyproject.toml', 'rb') as project_file:
    project = tomllib.load(project_file)['project']

version_string = project['version']
version_parts = tuple(int(part) for part in version_string.split('.'))
version_tuple = (version_parts + (0, 0, 0, 0))[:4]
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=version_tuple, prodvers=version_tuple),
    kids=[
        StringFileInfo([
            StringTable('040704B0', [
                StringStruct('CompanyName', 'IdentSpace'),
                StringStruct('FileDescription', 'IOHub Service'),
                StringStruct('FileVersion', version_string),
                StringStruct('InternalName', 'IOHub Service'),
                StringStruct('LegalCopyright', 'Copyright © 2026 IdentSpace'),
                StringStruct('OriginalFilename', 'IOHub Service.exe'),
                StringStruct('ProductName', 'IOHub Service'),
                StringStruct('ProductVersion', version_string),
            ]),
        ]),
        VarFileInfo([VarStruct('Translation', [1031, 1200])]),
    ],
)


a = Analysis(
    ['run.build.py'],
    pathex=[],
    binaries=[],
    datas=[('app', 'app'), ('pyproject.toml', '.'), *copy_metadata('APScheduler')],
    hiddenimports=['fastapi', 'uvicorn', 'sqlmodel', 'requests', 'aiosqlite', 'pystray._win32', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='IOHub Service',
    icon='app/assets/iohub.ico',
    version=version_info,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='IOHub Service',
)
