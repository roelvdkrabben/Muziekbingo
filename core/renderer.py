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

# Google Fonts URL-encoded family names (old UA → TTF response)
_SUPPORTED_FONTS: dict[str, str] = {
    "Inter":                "Inter:400,700",
    "EB Garamond":          "EB+Garamond:400,700",
    "Cormorant Garamond":   "Cormorant+Garamond:400,700",
    "Space Mono":           "Space+Mono:400,700",
    "Inconsolata":          "Inconsolata:400,700",
    "DM Sans":              "DM+Sans:400,700",
    "Playfair Display":     "Playfair+Display:400,700",
    "Bodoni Moda":          "Bodoni+Moda:400,700",
    "Tangerine":            "Tangerine:400,700",
    "Caveat":               "Caveat:400,700",
}

_OLD_UA = "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)"


def _font_filename(family: str, bold: bool) -> str:
    safe = family.replace(" ", "_")
    return f"{safe}-{'Bold' if bold else 'Regular'}.ttf"


def _ensure_font_family(family: str) -> None:
    if family not in _SUPPORTED_FONTS:
        logger.warning("Font '%s' niet ondersteund — val terug op Inter.", family)
        family = "Inter"
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    encoded = _SUPPORTED_FONTS[family]
    css_url = f"https://fonts.googleapis.com/css?family={encoded}"

    for bold in [False, True]:
        path = FONT_DIR / _font_filename(family, bold)
        if path.exists():
            continue
        try:
            req = urllib.request.Request(css_url, headers={"User-Agent": _OLD_UA})
            with urllib.request.urlopen(req, timeout=15) as resp:
                css = resp.read().decode("utf-8")
            ttf_urls = re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", css)
            if not ttf_urls:
                continue
            # first URL = regular (400), second = bold (700)
            target = ttf_urls[1] if bold and len(ttf_urls) > 1 else ttf_urls[0]
            with urllib.request.urlopen(target, timeout=15) as r:
                path.write_bytes(r.read())
            logger.info("Lettertype opgeslagen: %s", path.name)
        except Exception as exc:
            logger.warning("Lettertype download mislukt voor %s (%s): %s", family, "Bold" if bold else "Regular", exc)


def _ensure_fonts() -> None:
    _ensure_font_family("Inter")


def _load_font(bold: bool = False, size: int = 30, family: str = "Inter") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    _ensure_font_family(family)
    path = FONT_DIR / _font_filename(family, bold)
    if path.exists():
        try:
            return ImageFont.truetype(str(path), size)
        except Exception:
            pass
    # Fallback to Inter
    _ensure_font_family("Inter")
    fallback = FONT_DIR / ("Inter-Bold.ttf" if bold else "Inter-Regular.ttf")
    if fallback.exists():
        try:
            return ImageFont.truetype(str(fallback), size)
        except Exception:
            pass
    return ImageFont.load_default(size=size)


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


def _clean_title(title: str) -> str:
    return re.split(r'\s+[-(\[]|\s+feat\.|\s+ft\.', title, flags=re.IGNORECASE)[0].strip()


def _clip_text(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> str:
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
    title_align: str = "center",
    separator: str = " — ",
    vertical_align: str = "middle",
    free_center_logo: Optional[Image.Image] = None,
    cell_bg_opacity: int = 0,
) -> None:
    PAD = max(8, int(cell_w * 0.03))
    inner_w = cell_w - PAD * 2
    inner_h = cell_h - PAD * 2

    # Start with white cell; optionally blend template on top at cell_bg_opacity
    white = Image.new("RGBA", (cell_w, cell_h), (255, 255, 255, 255))
    if cell_bg_opacity > 0:
        tmpl = base.crop((x, y, x + cell_w, y + cell_h)).convert("RGBA")
        tmpl.putalpha(Image.new("L", (cell_w, cell_h), cell_bg_opacity))
        cell_rgb = Image.alpha_composite(white, tmpl).convert("RGB")
    else:
        cell_rgb = Image.new("RGB", (cell_w, cell_h), (255, 255, 255))
    base.paste(cell_rgb, (x, y))

    draw.rectangle([x, y, x + cell_w - 1, y + cell_h - 1], outline=(160, 150, 140), width=2)

    if is_free:
        if free_center_logo is not None:
            max_dim = min(inner_w, inner_h)
            logo = free_center_logo.copy()
            logo.thumbnail((max_dim, max_dim), Image.LANCZOS)
            lx = x + (cell_w - logo.width) // 2
            ly = y + (cell_h - logo.height) // 2
            if logo.mode == "RGBA":
                base.paste(logo, (lx, ly), logo)
            else:
                base.paste(logo.convert("RGB"), (lx, ly))
        else:
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

    title_lines = _wrap_text(draw, _clean_title(track.title), font_bold, inner_w)
    line_h_bold = draw.textbbox((0, 0), "Ag", font=font_bold)[3] + 6
    line_h_small = draw.textbbox((0, 0), "Ag", font=font_small)[3] + 4
    has_artist = bool(track.artist)
    has_sep = bool(separator)

    artist_lines: list[str] = []
    if has_artist:
        artist_lines = _wrap_text(draw, track.artist, font_small, inner_w)[:2]

    reserve_h = (line_h_small if has_sep else 0) + len(artist_lines) * line_h_small
    max_title_lines = max(1, int((text_h - reserve_h) / line_h_bold))
    title_lines = title_lines[:max_title_lines]

    total_text_h = len(title_lines) * line_h_bold + reserve_h
    if vertical_align == "middle":
        available_h = text_h if not (cover_img and show_cover_art) else (inner_h - (text_y - y - PAD))
        text_y = y + PAD + max(0, (available_h - total_text_h) // 2)

    cy = text_y
    for line in title_lines:
        draw.text((text_x, cy), line, font=font_bold, fill=(28, 26, 24), anchor=align_anchor)
        cy += line_h_bold

    if has_sep and cy < y + cell_h - PAD:
        draw.text((text_x, cy), separator, font=font_small, fill=(140, 130, 120), anchor=align_anchor)
        cy += line_h_small

    for artist_line in artist_lines:
        if cy < y + cell_h - PAD:
            draw.text((text_x, cy), artist_line, font=font_small, fill=(90, 80, 70), anchor=align_anchor)
            cy += line_h_small


def render_card(
    background: Image.Image,
    grid_rect: tuple[int, int, int, int],
    tracks: list[Track],
    show_cover_art: bool,
    free_space_label: str = "FREE",
    card_id: Optional[str] = None,
    font_scale: float = 1.0,
    separator: str = " — ",
    title_align: str = "center",
    vertical_align: str = "middle",
    artist_scale: float = 1.0,
    cell_title_font: str = "Inter",
    cell_artist_font: str = "Inter",
    free_center: bool = True,
    free_center_logo_path: Optional[str] = None,
    cell_bg_opacity: int = 0,
) -> Image.Image:
    songs_needed = 24 if free_center else 25
    assert len(tracks) == songs_needed, f"Verwacht {songs_needed} nummers, maar {len(tracks)} ontvangen."
    gx, gy, gw, gh = grid_rect
    cell_w = gw // 5
    cell_h = gh // 5

    base_size  = max(8, int(cell_h * 0.17 * font_scale))
    small_size = max(6, int(cell_h * 0.12 * artist_scale))

    font_bold  = _load_font(bold=True,  size=base_size,  family=cell_title_font)
    font_small = _load_font(bold=False, size=small_size, family=cell_artist_font)

    free_logo: Optional[Image.Image] = None
    if free_center and free_center_logo_path:
        try:
            free_logo = Image.open(free_center_logo_path).convert("RGBA")
        except Exception as exc:
            logger.warning("Vrij-vakje logo laden mislukt: %s", exc)

    card = background.copy().convert("RGB")
    draw = ImageDraw.Draw(card)

    grid = card_to_grid(tracks, free_center=free_center)

    for pos in range(25):
        row = pos // 5
        col = pos % 5
        cx = gx + col * cell_w
        cy = gy + row * cell_h
        is_free = free_center and pos == 12
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
            free_center_logo=free_logo,
            cell_bg_opacity=cell_bg_opacity,
        )

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
):
    """Yields one PIL Image per checklist page (generator — keeps memory low for large sets)."""
    MARGIN = 140
    font_title  = _load_font(bold=True,  size=60)
    font_header = _load_font(bold=True,  size=36)
    font_small  = _load_font(bold=False, size=24)

    cards_per_page = 4
    line_h_body = 36

    for page_start in range(0, len(cards), cards_per_page):
        page = Image.new("RGB", (page_w, page_h), (250, 247, 240))
        draw = ImageDraw.Draw(page)

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

            # Support both 24-track (free center) and 25-track (no free) cards
            free_center_cl = len(card_tracks) == 24
            grid = card_to_grid(card_tracks, free_center=free_center_cl)
            for pos, track in enumerate(grid):
                r = pos // 5
                c = pos % 5
                label = f"{r+1}×{c+1}"
                if track is None:
                    text = f"  {label}  FREE"
                    draw.text((bx, by), text, font=font_small, fill=(140, 40, 30))
                else:
                    entry_text = f"  {label}  {track.title} – {track.artist}"
                    while draw.textbbox((0, 0), entry_text, font=font_small)[2] > col_w - 40 and len(entry_text) > 20:
                        entry_text = entry_text[:-4] + "…"
                    draw.text((bx, by), entry_text, font=font_small, fill=(28, 26, 24))
                by += line_h_body

        yield page
