import subprocess
from pathlib import Path


def _ps(s: str) -> str:
    """PowerShell single-quoted literal."""
    return "'" + s.replace("'", "''") + "'"


def shortcut_script(target: Path, name: str) -> str:
    """PowerShell that creates <Desktop>/<name>.lnk to `target`, never replacing an existing one; prints the path."""
    return "; ".join([
        "$d = [Environment]::GetFolderPath('Desktop')",
        f"$l = Join-Path $d {_ps(name + '.lnk')}",
        "if (-not (Test-Path -LiteralPath $l)) { "
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($l); "
        f"$s.TargetPath = {_ps(str(target))}; "
        f"$s.WorkingDirectory = {_ps(str(target.parent))}; "
        f"$s.IconLocation = {_ps(str(target) + ',0')}; "
        "$s.Save() }",
        "Write-Output $l",
    ])


def create_desktop_shortcut(target: Path, name: str = "Hookshot Notes") -> Path:
    out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", shortcut_script(target, name)],
                         capture_output=True, text=True, timeout=30, check=True)
    return Path(out.stdout.strip().splitlines()[-1])
