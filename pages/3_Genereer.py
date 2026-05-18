import io
import random
import zipfile
from pathlib import Path

import img2pdf
import re as _re

def _clean_cards(cards):
    """Strip everything from first space+(-/([) onwards."""
    result = []
    for card in cards:
        clean = []
        for t in card:
            title = _re.split(r' [-(\[]', t.title)[0].strip()
            clean.append(_Track(t.spotify_id, title, t.artist, t.album, t.cover_url_300, t.cover_url_64))
        result.append(clean)
    return result

import streamlit as st
from PIL import Image

from app import check_password
from core.models import Track as _Track
from core.card_generator import generate_card_set
from core.pdf_builder import compose_pages
from core.renderer import render_card, render_checklist_pages
from db.storage import (
    init_db,
    list_playlists,
    list_designs,
    load_playlist,
    save_card_set,
)

st.set_page_config(page_title="Genereer — MuziekBingo", layout="wide")
init_db()

if not check_password():
    st.stop()

EXPORTS_DIR = Path("data/exports")
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

st.title("Kaarten genereren")

# ── Selectors ──────────────────────────────────────────────────────────────────
playlists = list_playlists()
designs = list_designs()

if not playlists:
    st.warning("Geen playlists gevonden. Ga eerst naar **Playlist** om een playlist op te halen.")
    st.stop()

if not designs:
    st.warning("Geen designs gevonden. Ga eerst naar **Design** om een design op te slaan.")
    st.stop()

col_left, col_right = st.columns([2, 1])

with col_left:
    playlist_options = {f"{p['name']} ({p['track_count']} nrs)": p for p in playlists}
    selected_pl_label = st.selectbox("Playlist", list(playlist_options.keys()))
    selected_pl = playlist_options[selected_pl_label]
    num_tracks = selected_pl["track_count"]

    design_options = {f"{d.name}": d for d in designs}
    selected_design_label = st.selectbox("Design", list(design_options.keys()))
    selected_design = design_options[selected_design_label]

with col_right:
    num_cards = st.slider("Aantal kaarten", min_value=1, max_value=300, value=30)

    songs_per_card = 24 if selected_design.free_center else 25
    ratio = num_cards * songs_per_card / num_tracks if num_tracks > 0 else 0
    if ratio > 6:
        st.warning(
            f"Verhouding kaarten/nummers is **{ratio:.1f}x** — overlap zal hoog zijn. "
            "Gebruik meer nummers of genereer minder kaarten."
        )

    card_name_pattern = st.text_input("Kaart-ID patroon", value="BINGO-{:03d}",
                                       help="Gebruik {:03d} voor oplopende nummering.")
    seed = st.number_input("Seed (voor reproduceerbaarheid)", min_value=0, max_value=999999,
                            value=random.randint(0, 99999), step=1)
    show_cover_art = st.toggle("Cover art tonen op kaarten", value=False)

st.markdown("---")

# ── Output format ──────────────────────────────────────────────────────────────
st.subheader("Uitvoerformaat")
output_format = st.radio(
    "Kies uitvoerformaat",
    ["PDF", "PNG (ZIP — losse kaarten)", "Beide"],
    horizontal=True,
)

want_pdf = output_format in ["PDF", "Beide"]
want_png = output_format in ["PNG (ZIP — losse kaarten)", "Beide"]

if want_pdf:
    cards_per_page = st.select_slider(
        "Kaarten per pagina (PDF)",
        options=[1, 2, 4],
        value=2,
        help="1 = portrait A4 beeldvullend · 2 = landscape A4 (gekanteld), 2 kaarten naast elkaar · 4 = portrait A4, 2×2 grid",
    )
    margin_mm = st.slider(
        "Kantmarge (mm)",
        min_value=0, max_value=20, value=5,
        help="Ruimte rondom de kaarten op de pagina. 0 = kaarten tot aan de rand.",
    )
    margin_px = int(margin_mm * 300 / 25.4)
    show_cut_marks = st.toggle(
        "Snijrand tonen",
        value=True,
        help="Snijlijnen worden afgedrukt als hulplijnen voor het knippen. Alleen zichtbaar bij 2 of 4 kaarten per pagina.",
    )
    cut_mark_width = st.slider("Dikte snijlijn (px)", min_value=1, max_value=10, value=3) if show_cut_marks else 3
else:
    cards_per_page = 1
    margin_px = 59
    show_cut_marks = False
    cut_mark_width = 3

set_name = st.text_input("Naam voor deze kaartset", value=f"{selected_pl['name']} — {num_cards} kaarten")

# ── Preview ────────────────────────────────────────────────────────────────────
st.subheader("PDF-voorbeeld")
st.caption(
    "Genereer een voorbeeld van één PDF-pagina met de huidige instellingen. "
    "Pas de opties hierboven aan en klik opnieuw om het effect te zien."
)

if st.button("Genereer PDF-voorbeeld", key="pdf_preview_btn"):
    _result = load_playlist(selected_pl["id"])
    if not _result:
        st.error("Playlist niet gevonden.")
    else:
        _, _tracks = _result
        _design = selected_design
        _img_path = Path(_design.image_path)
        if not _img_path.exists():
            st.error(f"Achtergrondafbeelding niet gevonden: {_img_path}")
        else:
            try:
                n_sample = cards_per_page if want_pdf else 1
                _songs_per_card = 24 if _design.free_center else 25
                _cards, _ = generate_card_set(_tracks, n_sample, songs_per_card=_songs_per_card, seed=int(seed))
                _cards = _clean_cards(_cards)
                _bg = Image.open(_img_path).convert("RGB")
                _rendered_preview = [
                    render_card(
                        background=_bg,
                        grid_rect=_design.grid_rect,
                        tracks=_cards[k],
                        show_cover_art=show_cover_art,
                        card_id=card_name_pattern.format(k + 1),
                        font_scale=_design.font_scale,
                        separator=_design.separator,
                        title_align=_design.title_align,
                        vertical_align=_design.vertical_align,
                        artist_scale=_design.artist_scale,
                        cell_title_font=_design.cell_title_font,
                        cell_artist_font=_design.cell_artist_font,
                        free_center=_design.free_center,
                        free_center_logo_path=_design.free_center_logo_path,
                        cell_bg_opacity=_design.cell_bg_opacity,
                    )
                    for k in range(n_sample)
                ]
                # Always show single card preview first (true-to-scale)
                _single = _rendered_preview[0]
                disp_w = 600
                disp_h = int(disp_w * _single.height / _single.width)
                st.image(
                    _single.resize((disp_w, disp_h), Image.LANCZOS),
                    caption="Voorbeeld kaart 1 — ware lettergrootte/stijl",
                )

                if want_pdf and cards_per_page > 1:
                    _preview_pages = compose_pages(
                        _rendered_preview,
                        cards_per_page,
                        margin_px=margin_px,
                        show_cut_marks=show_cut_marks,
                        cut_mark_width=cut_mark_width,
                    )
                    _page_img = _preview_pages[0]
                    _page_disp_w = 800
                    _page_disp_h = int(_page_disp_w * _page_img.height / _page_img.width)
                    _page_caption = (
                        f"PDF-layout: {cards_per_page} kaarten per pagina · "
                        f"marge {margin_mm}mm · "
                        + ("snijrand aan" if show_cut_marks else "snijrand uit")
                    )
                    st.image(
                        _page_img.resize((_page_disp_w, _page_disp_h), Image.LANCZOS),
                        caption=_page_caption,
                    )
            except Exception as _exc:
                st.error(f"Preview mislukt: {_exc}")

# ── Info panel ─────────────────────────────────────────────────────────────────
with st.expander("Hoe werkt de generatie?", expanded=False):
    st.markdown(f"""
**Playlist:** {num_tracks} nummers · **Kaarten:** {num_cards} · **Overlap verwacht:** gemiddeld ~{min(24, 24*24/max(num_tracks,1)):.1f} gedeelde nummers per kaartenpaar
**Seed:** {seed} — noteer deze om later exact dezelfde set te reproduceren.
""")

# ── Generate ───────────────────────────────────────────────────────────────────
if st.button("Genereer kaarten", type="primary"):
    result = load_playlist(selected_pl["id"])
    if not result:
        st.error("Playlist niet gevonden in de database.")
        st.stop()
    _, tracks = result

    design = selected_design

    img_path = Path(design.image_path)
    if not img_path.exists():
        st.error(f"Achtergrondafbeelding niet gevonden: {img_path}")
        st.stop()

    progress = st.progress(0, text="Kaarten genereren…")
    try:
        songs_per_card_gen = 24 if design.free_center else 25
        cards, stats = generate_card_set(tracks, num_cards, songs_per_card=songs_per_card_gen, seed=int(seed))
        cards = _clean_cards(cards)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    progress.progress(20, text="Kaarten gegenereerd — achtergrond laden…")

    background = Image.open(img_path).convert("RGB")
    grid_rect = design.grid_rect

    card_ids = [card_name_pattern.format(i + 1) for i in range(num_cards)]

    # Streaming render: nooit meer dan cards_per_page PIL-images tegelijk in geheugen.
    # Kaartpagina's worden direct gecomprimeerd naar JPEG-bytes; de PIL-images worden
    # daarna vrijgegeven. Voor 300 kaarten scheelt dit ~7 GB werkgeheugen.
    rendered_first: Image.Image | None = None
    page_jpegs: list[bytes] = []   # gecomprimeerde A4-pagina's voor PDF
    card_pngs: list[tuple[str, bytes]] = []  # (card_id, png_bytes) voor ZIP
    page_buffer: list[Image.Image] = []

    def _render(card, cid):
        return render_card(
            background=background,
            grid_rect=grid_rect,
            tracks=card,
            show_cover_art=show_cover_art,
            card_id=cid,
            font_scale=design.font_scale,
            separator=design.separator,
            title_align=design.title_align,
            vertical_align=design.vertical_align,
            artist_scale=design.artist_scale,
            cell_title_font=design.cell_title_font,
            cell_artist_font=design.cell_artist_font,
            free_center=design.free_center,
            free_center_logo_path=design.free_center_logo_path,
            cell_bg_opacity=design.cell_bg_opacity,
        )

    for i, (card, cid) in enumerate(zip(cards, card_ids)):
        img = _render(card, cid)

        if rendered_first is None:
            rendered_first = img  # bewaar alleen de eerste kaart voor preview

        if want_png:
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="PNG")
            card_pngs.append((cid, buf.getvalue()))

        if want_pdf:
            page_buffer.append(img)
            is_last = (i == num_cards - 1)
            if len(page_buffer) == cards_per_page or is_last:
                page = compose_pages(page_buffer, cards_per_page, margin_px, show_cut_marks, cut_mark_width)[0]
                buf = io.BytesIO()
                page.save(buf, format="JPEG", quality=92, dpi=(300, 300))
                page_jpegs.append(buf.getvalue())
                del page
                page_buffer = []  # PIL-images worden vrijgegeven (behalve rendered_first)

        progress.progress(20 + int(60 * (i + 1) / num_cards),
                          text=f"Kaart {i + 1}/{num_cards} renderen…")

    if want_pdf:
        progress.progress(82, text="Checklistpagina's genereren…")
        for cl_page in render_checklist_pages(cards, card_ids):
            buf = io.BytesIO()
            cl_page.save(buf, format="JPEG", quality=92, dpi=(300, 300))
            page_jpegs.append(buf.getvalue())
            del cl_page

    progress.progress(85, text="Opslaan…")

    cs_id = save_card_set(
        name=set_name,
        playlist_id=selected_pl["id"],
        design_id=design.id,
        num_cards=num_cards,
        show_cover_art=show_cover_art,
        seed=int(seed),
        cards=cards,
        stats=stats,
    )

    progress.progress(90, text="Exporteren…")

    pdf_bytes = zip_bytes = None

    if want_pdf:
        pdf_bytes = img2pdf.convert(page_jpegs)

    if want_png:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for cid, png_data in card_pngs:
                safe_id = cid.replace("/", "-").replace("\\", "-")
                zf.writestr(f"kaart_{safe_id}.png", png_data)
        zip_bytes = zip_buf.getvalue()

    progress.progress(100, text="Klaar!")

    st.success(f"{num_cards} kaarten gegenereerd en opgeslagen (set #{cs_id}).")
    s = stats
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Max. overlap", f"{s['max_overlap_observed']}/24")
    col2.metric("Gem. overlap", f"{s['avg_overlap']:.1f}/24")
    col3.metric("Theoretisch min.", f"{s['theoretical_min_avg_overlap']:.1f}")
    col4.metric("Ongebruikte nrs.", s["tracks_unused"])

    max_ov = s["max_overlap_observed"]
    if max_ov <= 9:
        st.success("Overlap ziet er goed uit!")
    elif max_ov <= 12:
        st.warning(f"Overlap is acceptabel maar hoog ({max_ov}/24). Overweeg meer nummers.")
    else:
        st.error(f"Hoge overlap ({max_ov}/24). Gebruik een grotere playlist.")

    st.subheader("Preview — kaart 1")
    thumb = rendered_first.resize((500, int(500 * rendered_first.height / rendered_first.width)), Image.LANCZOS)
    st.image(thumb)

    st.markdown("---")
    st.subheader("Downloaden")
    dl_col1, dl_col2 = st.columns(2)

    safe_name = set_name.replace(" ", "_").replace("/", "-")[:40]

    if pdf_bytes:
        dl_col1.download_button(
            label="Download PDF",
            data=pdf_bytes,
            file_name=f"{safe_name}.pdf",
            mime="application/pdf",
        )

    if zip_bytes:
        dl_col2.download_button(
            label="Download PNG (ZIP)",
            data=zip_bytes,
            file_name=f"{safe_name}_kaarten.zip",
            mime="application/zip",
        )
