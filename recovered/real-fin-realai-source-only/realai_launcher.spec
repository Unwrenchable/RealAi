# realai_launcher.spec
#
# PyInstaller spec file for building RealAI as a standalone Windows .exe.
#
# Prerequisites
# -------------
#   pip install pyinstaller
#
# Build
# -----
#   pyinstaller realai_launcher.spec
#
# Output
# ------
#   dist\RealAI.exe   (single-file executable; double-click to run)
#
# Notes
# -----
# * The GUI uses tkinter, which ships with the official Python Windows installer.
#   If you installed Python from the Microsoft Store you may need to reinstall
#   from python.org and tick "tcl/tk and IDLE" during setup.
# * To add a custom icon, set icon='icon.ico' in the EXE() call below.

block_cipher = None

a = Analysis(
    ['realai_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Bundle the core module and server alongside the GUI.
        ('realai.py', '.'),
        ('api_server.py', '.'),
        ('plugins', 'plugins'),
    ],
    hiddenimports=[
        'realai',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='RealAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,   # No console window — pure GUI app
    icon=None,       # Replace with 'icon.ico' to set a custom taskbar icon
)
