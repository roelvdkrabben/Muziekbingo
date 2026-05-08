"""Run once to pre-download Inter font files for the renderer."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.renderer import _ensure_fonts

if __name__ == "__main__":
    print("Lettertypen downloaden…")
    _ensure_fonts()
    font_dir = Path("assets/fonts")
    for f in font_dir.iterdir():
        print(f"  ✅ {f.name} ({f.stat().st_size // 1024} KB)")
    print("Klaar.")
