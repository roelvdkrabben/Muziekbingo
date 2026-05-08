import io
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

from core.renderer import render_checklist_pages

A4_W = 2480   # portrait width  (210mm @ 300dpi)
A4_H = 3508   # portrait height (297mm @ 300dpi)
MARGIN_PX = 59  # ~5mm at 300 DPI — tight bleed margin

def _fit_card(card: Image.Image, max_w: int, max_h: int) -> Image.Image:
    scale = min(max_w / card.width, max_h / card.height)
    return card.resize((int(card.width * scale), int(card.height * scale)), Image.LANCZOS)


def _paste_centered(page: Image.Image, card: Image.Image, cx: int, cy: int, w: int, h: int) -> None:
    fitted = _fit_card(card, w, h)
    ox = cx + (w - fitted.width) // 2
    oy = cy + (h - fitted.height) // 2
    page.paste(fitted, (ox, oy))


def _cut_line(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    draw.line([(x1, y1), (x2, y2)], fill=(160, 150, 140), width=3)
    # small scissors tick marks every 200px
    dx, dy = x2 - x1, y2 - y1
    length = (dx ** 2 + dy ** 2) ** 0.5
    if length == 0:
        return
    steps = max(1, int(length / 300))
    for s in range(1, steps):
        t = s / steps
        mx, my = int(x1 + dx * t), int(y1 + dy * t)
        if dy == 0:  # horizontal line → vertical tick
            draw.line([(mx, my - 20), (mx, my + 20)], fill=(160, 150, 140), width=2)
        else:        # vertical line → horizontal tick
            draw.line([(mx - 20, my), (mx + 20, my)], fill=(160, 150, 140), width=2)


def _compose_pages(
    rendered_cards: list[Image.Image],
    cards_per_page: int,
) -> list[Image.Image]:
    """
    Layout rules (beeldvullend / bleed):
      1 per page  → portrait A4  (2480×3508), 1 card fills page
      2 per page  → landscape A4 (3508×2480), 2 portrait cards side by side
      4 per page  → portrait A4  (2480×3508), 2×2 grid of portrait cards
    """
    pages: list[Image.Image] = []
    M = MARGIN_PX

    if cards_per_page == 1:
        for card in rendered_cards:
            page = Image.new("RGB", (A4_W, A4_H), (255, 255, 255))
            _paste_centered(page, card, M, M, A4_W - M * 2, A4_H - M * 2)
            pages.append(page)

    elif cards_per_page == 2:
        # Landscape page: A4 rotated → width=A4_H, height=A4_W
        PW, PH = A4_H, A4_W  # 3508 × 2480
        slot_w = (PW - M * 3) // 2
        slot_h = PH - M * 2
        for i in range(0, len(rendered_cards), 2):
            page = Image.new("RGB", (PW, PH), (255, 255, 255))
            draw = ImageDraw.Draw(page)
            _paste_centered(page, rendered_cards[i], M, M, slot_w, slot_h)
            if i + 1 < len(rendered_cards):
                _paste_centered(page, rendered_cards[i + 1], M * 2 + slot_w, M, slot_w, slot_h)
            cut_x = M + slot_w + M // 2
            _cut_line(draw, cut_x, M // 2, cut_x, PH - M // 2)
            pages.append(page)

    elif cards_per_page == 4:
        slot_w = (A4_W - M * 3) // 2
        slot_h = (A4_H - M * 3) // 2
        for i in range(0, len(rendered_cards), 4):
            page = Image.new("RGB", (A4_W, A4_H), (255, 255, 255))
            draw = ImageDraw.Draw(page)
            positions = [
                (M,          M),
                (M * 2 + slot_w, M),
                (M,          M * 2 + slot_h),
                (M * 2 + slot_w, M * 2 + slot_h),
            ]
            for j, (px, py) in enumerate(positions):
                if i + j < len(rendered_cards):
                    _paste_centered(page, rendered_cards[i + j], px, py, slot_w, slot_h)
            cut_x = M + slot_w + M // 2
            cut_y = M + slot_h + M // 2
            _cut_line(draw, cut_x, M // 2, cut_x, A4_H - M // 2)
            _cut_line(draw, M // 2, cut_y, A4_W - M // 2, cut_y)
            pages.append(page)

    return pages


def build_pdf(
    rendered_cards: list[Image.Image],
    cards_per_page: int,
    output_path: Path,
    cards_metadata: list[dict],
    card_tracks: list[list],
    card_ids: list[str],
) -> None:
    """
    Write multi-page PDF to `output_path`.
    Appends DJ checklist pages at the end.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pages = _compose_pages(rendered_cards, cards_per_page)
    checklist_pages = render_checklist_pages(card_tracks, card_ids)
    all_pages = pages + checklist_pages

    if not all_pages:
        raise ValueError("Geen pagina's om op te slaan.")

    first = all_pages[0].convert("RGB")
    rest = [p.convert("RGB") for p in all_pages[1:]]
    first.save(output_path, save_all=True, append_images=rest, resolution=300)


def build_png_zip(
    rendered_cards: list[Image.Image],
    card_ids: list[str],
    output_path: Path,
) -> None:
    """Write a ZIP archive with one PNG per card."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for card_img, cid in zip(rendered_cards, card_ids):
            buf = io.BytesIO()
            card_img.convert("RGB").save(buf, format="PNG")
            buf.seek(0)
            safe_id = cid.replace("/", "-").replace("\\", "-")
            zf.writestr(f"kaart_{safe_id}.png", buf.read())


def rendered_cards_to_pdf_bytes(
    rendered_cards: list[Image.Image],
    cards_per_page: int,
    card_tracks: list[list],
    card_ids: list[str],
) -> bytes:
    """Return PDF as bytes (for st.download_button)."""
    buf = io.BytesIO()
    pages = _compose_pages(rendered_cards, cards_per_page)
    checklist_pages = render_checklist_pages(card_tracks, card_ids)
    all_pages = pages + checklist_pages
    first = all_pages[0].convert("RGB")
    rest = [p.convert("RGB") for p in all_pages[1:]]
    first.save(buf, format="PDF", save_all=True, append_images=rest, resolution=300)
    return buf.getvalue()


def rendered_cards_to_zip_bytes(
    rendered_cards: list[Image.Image],
    card_ids: list[str],
) -> bytes:
    """Return ZIP of card PNGs as bytes (for st.download_button)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for card_img, cid in zip(rendered_cards, card_ids):
            card_buf = io.BytesIO()
            card_img.convert("RGB").save(card_buf, format="PNG")
            card_buf.seek(0)
            safe_id = cid.replace("/", "-").replace("\\", "-")
            zf.writestr(f"kaart_{safe_id}.png", card_buf.read())
    return buf.getvalue()
