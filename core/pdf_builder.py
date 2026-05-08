import io
import zipfile
from pathlib import Path

from PIL import Image

from core.renderer import render_checklist_pages

A4_W = 2480
A4_H = 3508
MARGIN_PX = 118  # ~10mm at 300 DPI


def _fit_card(card: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Scale card to fit within (max_w, max_h) preserving aspect ratio."""
    scale = min(max_w / card.width, max_h / card.height)
    new_w = int(card.width * scale)
    new_h = int(card.height * scale)
    return card.resize((new_w, new_h), Image.LANCZOS)


def _paste_centered(page: Image.Image, card: Image.Image, cx: int, cy: int, w: int, h: int) -> None:
    """Paste `card` centered in the rectangle (cx, cy, cx+w, cy+h)."""
    fitted = _fit_card(card, w, h)
    ox = cx + (w - fitted.width) // 2
    oy = cy + (h - fitted.height) // 2
    page.paste(fitted, (ox, oy))


def _new_page() -> Image.Image:
    return Image.new("RGB", (A4_W, A4_H), (255, 255, 255))


def _compose_pages(
    rendered_cards: list[Image.Image],
    cards_per_page: int,
) -> list[Image.Image]:
    pages: list[Image.Image] = []

    if cards_per_page == 1:
        for card in rendered_cards:
            page = _new_page()
            _paste_centered(page, card, MARGIN_PX, MARGIN_PX, A4_W - MARGIN_PX * 2, A4_H - MARGIN_PX * 2)
            pages.append(page)

    elif cards_per_page == 2:
        slot_h = (A4_H - MARGIN_PX * 3) // 2
        slot_w = A4_W - MARGIN_PX * 2
        for i in range(0, len(rendered_cards), 2):
            page = _new_page()
            _paste_centered(page, rendered_cards[i], MARGIN_PX, MARGIN_PX, slot_w, slot_h)
            if i + 1 < len(rendered_cards):
                _paste_centered(page, rendered_cards[i + 1], MARGIN_PX, MARGIN_PX * 2 + slot_h, slot_w, slot_h)
            # cut line
            cut_y = MARGIN_PX + slot_h + MARGIN_PX // 2
            from PIL import ImageDraw
            draw = ImageDraw.Draw(page)
            draw.line([(MARGIN_PX, cut_y), (A4_W - MARGIN_PX, cut_y)], fill=(180, 170, 160), width=4)
            pages.append(page)

    elif cards_per_page == 4:
        slot_w = (A4_W - MARGIN_PX * 3) // 2
        slot_h = (A4_H - MARGIN_PX * 3) // 2
        from PIL import ImageDraw
        for i in range(0, len(rendered_cards), 4):
            page = _new_page()
            positions = [
                (MARGIN_PX, MARGIN_PX),
                (MARGIN_PX * 2 + slot_w, MARGIN_PX),
                (MARGIN_PX, MARGIN_PX * 2 + slot_h),
                (MARGIN_PX * 2 + slot_w, MARGIN_PX * 2 + slot_h),
            ]
            for j, (px, py) in enumerate(positions):
                if i + j < len(rendered_cards):
                    _paste_centered(page, rendered_cards[i + j], px, py, slot_w, slot_h)
            draw = ImageDraw.Draw(page)
            cut_x = MARGIN_PX + slot_w + MARGIN_PX // 2
            cut_y = MARGIN_PX + slot_h + MARGIN_PX // 2
            draw.line([(cut_x, MARGIN_PX // 2), (cut_x, A4_H - MARGIN_PX // 2)], fill=(180, 170, 160), width=4)
            draw.line([(MARGIN_PX // 2, cut_y), (A4_W - MARGIN_PX // 2, cut_y)], fill=(180, 170, 160), width=4)
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
