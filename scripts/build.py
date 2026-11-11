"""Package the skill as dist/quality-tea-leaves.zip for upload (Claude, Agensi or any SKILL.md agent).

Quality Tea Leaves, created by Jessica Mosley | LinkedIn: https://www.linkedin.com/in/jessmosley/ | GitHub: https://github.com/j-m-o/
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "quality-tea-leaves"
OUT = ROOT / "dist" / "quality-tea-leaves.zip"

OUT.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for path in sorted(SKILL.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            info = zipfile.ZipInfo(str(Path("quality-tea-leaves") / path.relative_to(SKILL)), date_time=(2026, 11, 11, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, path.read_bytes())
print(f"Built {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")
