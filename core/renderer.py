import logging
import re
import urllib.request
from pathlib import Path
from typing import Optional

import requests
from PIL import Image, ImageDraw, ImageFont

from core.models import Track
from core.card_generator import card_to_grid

logger = logging.getLogger(__name__)

FONT_DIR = Path(__file__).parent.parent / "assets" / "fonts"
COVERS_DIR = Path(__file__).parent.parent / "data" / "covers"

# Mapping: (family, weight) → filename
_FONT_FILES = {
    ("Inter", 400): "Inter-Regular.ttf",
    ("Inter", 700): "Inter-Bold.ttf",
}

# Known stable Google Fonts TTF URLs (old UA trick → TTF response)
_GOOGLE_FONT_URLS = {
    "Inter": "https://fonts.googleapis.com/css?family=Inter:400,700",
}


def _download_google_font_ttf(family: str) -> dict[int, bytes]:
    """Fetch TTF bytes for regular and bold weights from Google Fonts."""
    url = _GOOGLE_FONT_URLS[family]
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)"
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        css = resp.read().decode("utf-8")

    ttf_urls = re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)", css)
    results: dict[int, bytes] = {}

    for ttf_url in ttf_urls:
        with urllib.request.urlopen(ttf_url, timeout=15) as r:
            data = r.read()
        # Determine weight from context; first hit is regular (400), second is bold (700)
        weight = 400 if 400 not in results else 700
        results[weight] = data
        if len(results) >= 2:
            break

    return results


def _ensure_fonts() -> None:
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    regular = FONT_DIR / "Inter-Regular.ttf"
    bold = FONT_DIR / "Inter-Bold.ttf"

    if regular.exists() and bold.exists():
        return

    logger.info("Lettertypen worden gedownload van Google Fonts...")
    try:
        fonts = _download_google_font_ttf("Inter")
        if 400 in fonts:
            regular.write_bytes(fonts[400])
        if 700 in fonts:
            bold.write_bytes(fonts[700])
        logger.info("Lettertypen opgeslagen in %s", FONT_DIR)
    except Exception as exc:
        logger.warning("Lettertype download mislukt: %s — standaard lettertype wordt gebruikt.", exc)


def _load_font(bold: bool = False, size: int = 30) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    _ensure_fonts()
    fname = "Inter-Bold.ttf" if bold else "Inter-Regular.ttf"
    path = FONT_DIR / fname
    if path.exists():
        try:
            return ImageFont.truetype(str(path), size)
        except Exception:
            pass
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        test = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] > max_width and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines or [""]


def _fetch_cover(track: Track) -> Optional[Image.Image]:
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    if not track.cover_url_300:
        return None
    cache_path = COVERS_DIR / f"{track.spotify_id}.jpg"
    if not cache_path.exists():
        try:
            resp = requests.get(track.cover_url_300, timeout=10)
            resp.raise_for_status()
            cache_path.write_bytes(resp.content)
        except Exception as exc:
            logger.warning("Cover art download mislukt voor %s: %s", track.spotify_id, exc)
            return None
    try:
        return Image.open(cache_path).convert("RGB")
    except Exception:
        return None


def _clip_text(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> str:
    """Clip text with ellipsis to fit max_w pixels."""
    bbox = draw.textbbox((0, 0), text, font=font)
    while bbox[2] > max_w and len(text) > 2:
        text = text[:-2] + "…"
        bbox = draw.textbbox((0, 0), text, font=font)
    return text


def _draw_cell(
    draw: ImageDraw.ImageDraw,
    base: Image.Image,
    x: int,
    y: int,
    cell_w: int,
    cell_h: int,
    track: Optional[Track],
    show_cover_art: bool,
    free_label: str,
    font_bold,
    font_small,
    is_free: bool,
    title_align: str = "left",
    separator: str = " — ",
    vertical_align: str = "top",
) -> None:
    PAD = max(12, int(cell_w * 0.05))
    inner_w = cell_w - PAD * 2
    inner_h = cell_h - PAD * 2

    overlay = Image.new("RGBA", (cell_w, cell_h), (255, 255, 255, 130))
    base.paste(Image.alpha_composite(base.crop((x, y, x + cell_w, y + cell_h)).convert("RGBA"), overlay).convert("RGB"), (x, y))

    draw.rectangle([x, y, x + cell_w - 1, y + cell_h - 1], outline=(160, 150, 140), width=2)

    if is_free:
        total_h = draw.textbbox((0, 0), free_label, font=font_bold)[3]
        tx = x + cell_w // 2
        ty = y + (cell_h - total_h) // 2
        draw.text((tx, ty), free_label, font=font_bold, fill=(140, 40, 30), anchor="mt")
        return

    assert track is not None
    cover_img: Optional[Image.Image] = None
    if show_cover_art:
        cover_img = _fetch_cover(track)

    text_y = y + PAD
    text_h = inner_h

    if cover_img and show_cover_art:
        art_h = int(inner_h * 0.48)
        cover_resized = cover_img.resize((inner_w, art_h), Image.LANCZOS)
        base.paste(cover_resized, (x + PAD, y + PAD))
        text_y = y + PAD + art_h + PAD // 2
        text_h = inner_h - art_h - PAD // 2

    align_anchor = "lt" if title_align == "left" else "mt"
    text_x = x + PAD if title_align == "left" else x + cell_w // 2

    # title (bold, wrapped)
    title_lines = _wrap_text(draw, track.title, font_bold, inner_w)
    line_h_bold = draw.textbbox((0, 0), "Ag", font=font_bold)[3] + 4
    max_title_lines = max(1, int(text_h * 0.6 / line_h_bold))
    title_lines = title_lines[:max_title_lines]

    line_h_small = draw.textbbox((0, 0), "Ag", font=font_small)[3] + 4
    has_artist = bool(track.artist)
    total_text_h = len(title_lines) * line_h_bold + (line_h_small + 2 if has_artist else 0)

    if vertical_align == "middle":
        available_h = text_h if not (cover_img and show_cover_art) else (inner_h - (text_y - y - PAD))
        text_y = y + PAD + max(0, (available_h - total_text_h) // 2)

    cy = text_y
    for line in title_lines:
        draw.text((text_x, cy), line, font=font_bold, fill=(28, 26, 24), anchor=align_anchor)
        cy += line_h_bold

    # artist with separator prefix (one line, clipped)
    if has_artist and cy < y + cell_h - PAD:
        artist_line = _clip_text(draw, separator + track.artist, font_small, inner_w)
        draw.text((text_x, cy + 2), artist_line, font=font_small, fill=(90, 80, 70), anchor=align_anchor)


def render_card(
    background: Image.Image,
    grid_rect: tuple[int, int, int, int],
    tracks: list[Track],
    show_cover_art: bool,
    free_space_label: str = "FREE",
    card_id: Optional[str] = None,
    font_scale: float = 1.0,
    separator: str = " — ",
    title_align: str = "left",
    vertical_align: str = "top",
) -> Image.Image:
    """
    Composite a 5×5 bingo grid onto `background` at `grid_rect` (x, y, w, h).
    `tracks` must have exactly 24 items. Returns a new RGBA-composited RGB image.
    """
    assert len(tracks) == 24, f"Verwacht 24 nummers, maar {len(tracks)} ontvangen."
    gx, gy, gw, gh = grid_rect
    cell_w = gw // 5
    cell_h = gh // 5

    # Font sizes scale with cell dimensions — ~12pt and ~9pt at 300 DPI for default A4 grid
    base_size = max(36, int(cell_h * 0.12 * font_scale))
    small_size = max(28, int(cell_h * 0.09 * font_scale))

    font_bold = _load_font(bold=True, size=base_size)
    font_small = _load_font(bold=False, size=small_size)

    card = background.copy().convert("RGB")
    draw = ImageDraw.Draw(card)

    grid = card_to_grid(tracks)  # 25 items, None at index 12

    for pos in range(25):
        row = pos // 5
        col = pos % 5
        cx = gx + col * cell_w
        cy = gy + row * cell_h
        is_free = pos == 12
        track = grid[pos]

        _draw_cell(
            draw=draw,
            base=card,
            x=cx,
            y=cy,
            cell_w=cell_w,
            cell_h=cell_h,
            track=track,
            show_cover_art=show_cover_art,
            free_label=free_space_label,
            font_bold=font_bold,
            font_small=font_small,
            is_free=is_free,
            title_align=title_align,
            separator=separator,
            vertical_align=vertical_align,
        )

    # card ID in bottom-right corner
    if card_id:
        id_font = _load_font(bold=False, size=max(18, int(cell_h * 0.04)))
        margin = 30
        draw.text(
            (gx + gw - margin, gy + gh + margin // 2),
            card_id,
            font=id_font,
            fill=(100, 90, 80),
            anchor="rt",
        )

    return card


def render_checklist_pages(
    cards: list[list[Track]],
    card_ids: list[str],
    page_w: int = 2480,
    page_h: int = 3508,
) -> list[Image.Image]:
    """Render DJ checklist pages: one entry per card with its 24 tracks in grid order."""
    MARGIN = 140
    font_title = _load_font(bold=True, size=60)
    font_header = _load_font(bold=True, size=36)
    font_small = _load_font(bold=False, size=24)

    pages: list[Image.Image] = []
    cards_per_page = 4
    line_h_body = 36

    for page_start in range(0, len(cards), cards_per_page):
        page = Image.new("RGB", (page_w, page_h), (250, 247, 240))
        draw = ImageDraw.Draw(page)

        # header
        draw.text((MARGIN, 80), "DJ Checklist — MuziekBingo", font=font_title, fill=(28, 26, 24))
        draw.line([(MARGIN, 170), (page_w - MARGIN, 170)], fill=(180, 160, 140), width=3)

        col_w = (page_w - MARGIN * 2) // 2
        entries = cards[page_start:page_start + cards_per_page]

        for entry_idx, (card_tracks, cid) in enumerate(
            zip(entries, card_ids[page_start:page_start + cards_per_page])
        ):
            col = entry_idx % 2
            row_block = entry_idx // 2
            bx = MARGIN + col * col_w
            by = 200 + row_block * (page_h - 280) // 2

            draw.text((bx, by), f"Kaart {cid}", font=font_header, fill=(140, 40, 30))
            by += 55
            draw.line([(bx, by), (bx + col_w - 40, by)], fill=(200, 180, 160), width=2)
            by += 16

            grid = card_to_grid(card_tracks)
            for pos, track in enumerate(grid):
                r = pos // 5
                c = pos % 5
                label = f"{r+1}×{c+1}"
                if track is None:
                    text = f"  {label}  FREE"
                    draw.text((bx, by), text, font=font_small, fill=(140, 40, 30))
                else:
                    entry_text = f"  {label}  {track.title} – {track.artist}"
                    # clip to column width
                    while draw.textbbox((0, 0), entry_text, font=font_small)[2] > col_w - 40 and len(entry_text) > 20:
                        entry_text = entry_text[:-4] + "…"
                    draw.text((bx, by), entry_text, font=font_small, fill=(28, 26, 24))
                by += line_h_body

        pages.append(page)

    return pages
