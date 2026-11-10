# PyInstaller recipe: pyinstaller packaging/hookshot-notes.spec  ->  dist/hookshot-notes.exe
from pathlib import Path

root = Path(SPECPATH).parent

a = Analysis(
    [str(root / "packaging" / "entry.py")],
    pathex=[str(root)],
    datas=[(str(root / "hookshot_notes" / "web"), "hookshot_notes/web")],
    hiddenimports=["qrcode.image.svg", "texture2ddecoder", "tkinter", "tkinter.filedialog"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, name="hookshot-notes", console=True, upx=False)
