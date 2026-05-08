import io
import json
import random
from pathlib import Path

import streamlit as st
from PIL import Image

from app import check_password
from core.card_generator import generate_card_set
from core.pdf_builder import rendered_cards_to_pdf_bytes, rendered_cards_to_zip_bytes
from core.renderer import render_card
from db.storage import (
    init_db,
    list_playlists,
    list_designs,
    load_playlist,
    load_design,
    save_card_set,
)

st.set_page_config(page_title="Genereer — MuziekBingo", page_icon="🎲", layout="wide")
init_db()

if not check_password():
    st.stop()

EXPORTS_DIR = Path("data/exports")
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

st.title("🎲 Kaarten genereren")

# ── Selectors ──────────────────────────────────────────────────────────────────
playlists = list_playlists()
designs = list_designs()

if not playlists:
    st.warning("Geen playlists gevonden. Ga eerst naar **📥 Playlist** om een playlist op te halen.")
    st.stop()

if not designs:
    st.warning("Geen designs gevonden. Ga eerst naar **🎨 Design** om een design op te slaan.")
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

    ratio = num_cards * 24 / num_tracks if num_tracks > 0 else 0
    if ratio > 6:
        st.warning(
            f"⚠️ Verhouding kaarten/nummers is **{ratio:.1f}×** — overlap zal hoog zijn. "
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
    ["📄 PDF", "🖼 PNG (ZIP — losse kaarten)", "📄 + 🖼 Beide"],
    horizontal=True,
)

want_pdf = output_format in ["📄 PDF", "📄 + 🖼 Beide"]
want_png = output_format in ["🖼 PNG (ZIP — losse kaarten)", "📄 + 🖼 Beide"]

if want_pdf:
    cards_per_page = st.select_slider(
        "Kaarten per pagina (PDF)",
        options=[1, 2, 4],
        value=2,
        help="1 per A4 = premium; 2 per A4 = snijlijn; 4 per A4 = compact.",
    )
else:
    cards_per_page = 1

set_name = st.text_input("Naam voor deze kaartset", value=f"{selected_pl['name']} — {num_cards} kaarten")

# ── Info panel ─────────────────────────────────────────────────────────────────
with st.expander("ℹ️ Hoe werkt de generatie?", expanded=False):
    st.markdown(f"""
**Playlist:** {num_tracks} nummers · **Kaarten:** {num_cards} · **Overlap verwacht:** gemiddeld ~{min(24, 24*24/max(num_tracks,1)):.1f} gedeelde nummers per kaartenpaar
**Seed:** {seed} — noteer deze om later exact dezelfde set te reproduceren.
""")

# ── Generate ───────────────────────────────────────────────────────────────────
if st.button("🎲 Genereer kaarten", type="primary"):
    result = load_playlist(selected_pl["id"])
    if not result:
        st.error("Playlist niet gevonden in de database.")
        st.stop()
    _, tracks = result

    design = selected_design  # Design object from list_designs()

    img_path = Path(design.image_path)
    if not img_path.exists():
        st.error(f"Achtergrondafbeelding niet gevonden: {img_path}")
        st.stop()

    # Generate card set
    progress = st.progress(0, text="Kaarten genereren…")
    try:
        cards, stats = generate_card_set(tracks, num_cards, seed=int(seed))
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    progress.progress(20, text="Kaarten gegenereerd — achtergrond laden…")

    background = Image.open(img_path).convert("RGB")
    grid_rect = design.grid_rect

    card_ids = [card_name_pattern.format(i + 1) for i in range(num_cards)]

    # Render cards
    rendered: list[Image.Image] = []
    for i, (card, cid) in enumerate(zip(cards, card_ids)):
        rendered.append(render_card(
            background=background,
            grid_rect=grid_rect,
            tracks=card,
            show_cover_art=show_cover_art,
            card_id=cid,
        ))
        progress.progress(20 + int(60 * (i + 1) / num_cards),
                          text=f"Kaart {i + 1}/{num_cards} renderen…")

    progress.progress(82, text="Exporteren…")

    # ── Save to DB ─────────────────────────────────────────────────────────────
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

    # ── Build outputs ──────────────────────────────────────────────────────────
    pdf_bytes = zip_bytes = None

    if want_pdf:
        pdf_bytes = rendered_cards_to_pdf_bytes(
            rendered_cards=rendered,
            cards_per_page=cards_per_page,
            card_tracks=cards,
            card_ids=card_ids,
        )

    if want_png:
        zip_bytes = rendered_cards_to_zip_bytes(
            rendered_cards=rendered,
            card_ids=card_ids,
        )

    progress.progress(100, text="Klaar!")

    # ── Stats ──────────────────────────────────────────────────────────────────
    st.success(f"✅ {num_cards} kaarten gegenereerd en opgeslagen (set #{cs_id}).")
    s = stats
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Max. overlap", f"{s['max_overlap_observed']}/24")
    col2.metric("Gem. overlap", f"{s['avg_overlap']:.1f}/24")
    col3.metric("Theoretisch min.", f"{s['theoretical_min_avg_overlap']:.1f}")
    col4.metric("Ongebruikte nrs.", s["tracks_unused"])

    # overlap health indicator
    max_ov = s["max_overlap_observed"]
    if max_ov <= 9:
        st.success("Overlap ziet er goed uit! ✅")
    elif max_ov <= 12:
        st.warning(f"Overlap is acceptabel maar hoog ({max_ov}/24). Overweeg meer nummers.")
    else:
        st.error(f"Hoge overlap ({max_ov}/24). Gebruik een grotere playlist.")

    # ── Preview ────────────────────────────────────────────────────────────────
    st.subheader("Preview — kaart 1")
    thumb = rendered[0].resize((500, int(500 * rendered[0].height / rendered[0].width)), Image.LANCZOS)
    st.image(thumb)

    # ── Downloads ─────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Downloaden")
    dl_col1, dl_col2 = st.columns(2)

    safe_name = set_name.replace(" ", "_").replace("/", "-")[:40]

    if pdf_bytes:
        dl_col1.download_button(
            label="📄 Download PDF",
            data=pdf_bytes,
            file_name=f"{safe_name}.pdf",
            mime="application/pdf",
        )

    if zip_bytes:
        dl_col2.download_button(
            label="🖼 Download PNG (ZIP)",
            data=zip_bytes,
            file_name=f"{safe_name}_kaarten.zip",
            mime="application/zip",
        )
