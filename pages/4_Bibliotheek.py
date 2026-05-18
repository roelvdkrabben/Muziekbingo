import io
import zipfile
from pathlib import Path

import img2pdf
import streamlit as st
from PIL import Image

from app import check_password
from core.pdf_builder import compose_pages
from core.renderer import render_card, render_checklist_pages
from db.storage import (
    init_db,
    list_playlists,
    list_designs,
    list_card_sets,
    load_card_set,
    load_design,
    delete_card_set,
    delete_playlist,
    delete_design,
)

st.set_page_config(page_title="Bibliotheek — MuziekBingo", layout="wide")
init_db()

if not check_password():
    st.stop()

st.title("Bibliotheek")

tab_sets, tab_playlists, tab_designs = st.tabs(["Kaartsets", "Playlists", "Designs"])

# ── Card sets ──────────────────────────────────────────────────────────────────
with tab_sets:
    card_sets = list_card_sets()
    if not card_sets:
        st.info("Nog geen kaartsets gegenereerd.")
    else:
        for cs in card_sets:
            with st.expander(
                f"**{cs['name']}** — {cs['num_cards']} kaarten · seed {cs['seed']} · {cs['created_at'][:10]}",
                expanded=False,
            ):
                s = cs["stats"]
                col1, col2, col3 = st.columns(3)
                col1.metric("Max. overlap", f"{s.get('max_overlap_observed', '?')}/24")
                col2.metric("Gem. overlap", f"{s.get('avg_overlap', '?')}/24")
                col3.metric("Playlist-nummers", s.get("playlist_size", "?"))

                action_col1, action_col2, action_col3 = st.columns(3)

                if action_col1.button("Re-exporteer PDF", key=f"re_pdf_{cs['id']}"):
                    result = load_card_set(cs["id"])
                    if result:
                        cs_obj, cards = result
                        design = load_design(cs_obj.design_id)
                        if design and Path(design.image_path).exists():
                            background = Image.open(design.image_path).convert("RGB")
                            card_ids = [f"BINGO-{i+1:03d}" for i in range(len(cards))]
                            cards_per_page = 2
                            with st.spinner("Kaarten renderen…"):
                                page_jpegs: list[bytes] = []
                                page_buffer: list[Image.Image] = []
                                for i, (card, cid) in enumerate(zip(cards, card_ids)):
                                    img = render_card(background, design.grid_rect, card, cs_obj.show_cover_art, card_id=cid)
                                    page_buffer.append(img)
                                    is_last = (i == len(cards) - 1)
                                    if len(page_buffer) == cards_per_page or is_last:
                                        page = compose_pages(page_buffer, cards_per_page)[0]
                                        buf = io.BytesIO()
                                        page.save(buf, format="JPEG", quality=92, dpi=(300, 300))
                                        page_jpegs.append(buf.getvalue())
                                        del page
                                        page_buffer = []
                                for cl_page in render_checklist_pages(cards, card_ids):
                                    buf = io.BytesIO()
                                    cl_page.save(buf, format="JPEG", quality=92, dpi=(300, 300))
                                    page_jpegs.append(buf.getvalue())
                                    del cl_page
                                pdf_bytes = img2pdf.convert(page_jpegs)
                            safe = cs_obj.name.replace(" ", "_")[:40]
                            st.download_button(
                                "Download PDF",
                                data=pdf_bytes,
                                file_name=f"{safe}.pdf",
                                mime="application/pdf",
                                key=f"dl_pdf_{cs['id']}",
                            )
                        else:
                            st.error("Design of afbeelding niet gevonden.")

                if action_col2.button("Re-exporteer PNG ZIP", key=f"re_zip_{cs['id']}"):
                    result = load_card_set(cs["id"])
                    if result:
                        cs_obj, cards = result
                        design = load_design(cs_obj.design_id)
                        if design and Path(design.image_path).exists():
                            background = Image.open(design.image_path).convert("RGB")
                            card_ids = [f"BINGO-{i+1:03d}" for i in range(len(cards))]
                            with st.spinner("Kaarten renderen…"):
                                zip_buf = io.BytesIO()
                                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                                    for card, cid in zip(cards, card_ids):
                                        img = render_card(background, design.grid_rect, card, cs_obj.show_cover_art, card_id=cid)
                                        card_buf = io.BytesIO()
                                        img.convert("RGB").save(card_buf, format="PNG")
                                        del img
                                        safe_id = cid.replace("/", "-").replace("\\", "-")
                                        zf.writestr(f"kaart_{safe_id}.png", card_buf.getvalue())
                                zip_bytes = zip_buf.getvalue()
                            safe = cs_obj.name.replace(" ", "_")[:40]
                            st.download_button(
                                "Download ZIP",
                                data=zip_bytes,
                                file_name=f"{safe}_kaarten.zip",
                                mime="application/zip",
                                key=f"dl_zip_{cs['id']}",
                            )
                        else:
                            st.error("Design of afbeelding niet gevonden.")

                if action_col3.button("Verwijder set", key=f"del_cs_{cs['id']}"):
                    delete_card_set(cs["id"])
                    st.rerun()

# ── Playlists ──────────────────────────────────────────────────────────────────
with tab_playlists:
    playlists = list_playlists()
    if not playlists:
        st.info("Geen playlists opgeslagen.")
    else:
        for p in playlists:
            c1, c2, c3 = st.columns([4, 1, 1])
            c1.markdown(f"**{p['name']}** · {p['track_count']} nummers")
            c2.caption(p["fetched_at"][:10])
            if c3.button("Verwijder", key=f"lib_del_pl_{p['id']}"):
                delete_playlist(p["id"])
                st.rerun()

# ── Designs ────────────────────────────────────────────────────────────────────
with tab_designs:
    designs = list_designs()
    if not designs:
        st.info("Geen designs opgeslagen.")
    else:
        for d in designs:
            c1, c2, c3 = st.columns([4, 1, 1])
            c1.markdown(f"**{d.name}**")
            c2.caption(d.created_at.strftime("%d-%m-%Y"))
            if c3.button("Verwijder", key=f"lib_del_des_{d.id}"):
                delete_design(d.id)
                st.rerun()
            img_path = Path(d.image_path)
            if img_path.exists():
                with st.expander("Bekijk", expanded=False):
                    thumb = Image.open(img_path).resize((300, int(300 * 3508 / 2480)), Image.LANCZOS)
                    st.image(thumb)
