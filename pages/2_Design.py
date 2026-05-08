import base64
import io
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw

from app import check_password
from core.renderer import render_card
from db.storage import init_db, save_design, list_designs, delete_design, update_design_grid, update_design_style, list_playlists, load_playlist
from designer_component import designer_component

st.set_page_config(page_title="Design — MuziekBingo", layout="wide")
init_db()

if not check_password():
    st.stop()

DESIGNS_DIR = Path("data/designs")
DESIGNS_DIR.mkdir(parents=True, exist_ok=True)

st.title("Design")

tab_designer, tab_upload = st.tabs(["Designer", "Upload eigen PNG"])


def _draw_grid_overlay(img: Image.Image, gx: int, gy: int, gw: int, gh: int) -> Image.Image:
    """Return a copy of img with a 5×5 grid overlay drawn."""
    out = img.copy().convert("RGB")
    draw = ImageDraw.Draw(out)
    cell_w = gw // 5
    cell_h = gh // 5
    lw = max(3, img.width // 400)
    for r in range(6):
        y = gy + r * cell_h
        draw.line([(gx, y), (gx + gw, y)], fill=(220, 40, 40), width=lw)
    for c in range(6):
        x = gx + c * cell_w
        draw.line([(x, gy), (x, gy + gh)], fill=(220, 40, 40), width=lw)
    # outer rect
    draw.rectangle([gx, gy, gx + gw, gy + gh], outline=(220, 40, 40), width=lw * 2)
    return out


# ── Tab 1: Embedded designer ───────────────────────────────────────────────────
with tab_designer:

    pending = st.session_state.get("designer_pending")
    if pending:
        st.success("Achtergrond ontvangen van de designer — sla hem hieronder op.")
        gr = pending["grid_rect"]
        col_prev, col_form = st.columns([1, 1])
        with col_prev:
            png_bytes = base64.b64decode(pending["png_base64"])
            thumb = Image.open(io.BytesIO(png_bytes)).convert("RGB").resize(
                (380, int(380 * 3508 / 2480)), Image.LANCZOS
            )
            st.image(thumb, caption="Preview")
        with col_form:
            design_name = st.text_input(
                "Naam voor dit design",
                value=pending.get("title", "Mijn design"),
                key="des_name_designer",
            )
            # grid_rect comes from computeGridRect() in full PAGE coords (2480×3508) — use as-is
            full_w, full_h = 2480, 3508
            gr_full = {k: int(v) for k, v in gr.items()}
            st.caption(
                f"Rastergebied (automatisch): "
                f"x={gr_full['x']}, y={gr_full['y']}, b={gr_full['w']}, h={gr_full['h']}"
            )
            c1, c2 = st.columns(2)
            if c1.button("Design opslaan", type="primary", key="save_designer"):
                fname = design_name.replace(" ", "_")[:40] + ".png"
                save_path = DESIGNS_DIR / fname
                img_from_designer = (
                    Image.open(io.BytesIO(png_bytes))
                    .convert("RGB")
                    .resize((full_w, full_h), Image.LANCZOS)
                )
                img_from_designer.save(str(save_path), format="PNG")
                save_design(
                    name=design_name,
                    image_path=str(save_path),
                    grid_x=gr_full["x"],
                    grid_y=gr_full["y"],
                    grid_w=gr_full["w"],
                    grid_h=gr_full["h"],
                )
                del st.session_state["designer_pending"]
                st.success(f"Design **{design_name}** opgeslagen.")
                st.rerun()
            if c2.button("Annuleren", key="cancel_designer"):
                del st.session_state["designer_pending"]
                st.rerun()
        st.markdown("---")

    st.caption(
        "Ontwerp je achtergrond hieronder. Klik **'Gebruik als achtergrond'** (rechts in de balk) "
        "om het design op te sturen — het formulier verschijnt hierboven."
    )

    result = designer_component(key="bg_designer")

    if result is not None:
        st.caption(f"Component waarde ontvangen — png: {'ja' if result.get('png_base64') else 'nee'}, grid: {result.get('grid_rect')}")

    if result and result != st.session_state.get("designer_pending"):
        st.session_state["designer_pending"] = result
        st.rerun()

# ── Tab 2: Upload custom PNG ───────────────────────────────────────────────────
with tab_upload:
    st.caption(
        "Upload een eigen PNG en markeer waar het 5×5 raster moet komen."
    )

    uploaded = st.file_uploader("Achtergrond uploaden (PNG of JPG)", type=["png", "jpg", "jpeg"])

    if uploaded:
        bg = Image.open(uploaded).convert("RGB")
        orig_w, orig_h = bg.size

        st.info(
            f"Afbeelding: **{orig_w} × {orig_h} px**  "
            f"({'A4 300 DPI' if orig_w == 2480 and orig_h == 3508 else 'Let op: niet A4 300 DPI formaat'})"
        )

        method = st.radio(
            "Hoe wil je het rastergebied instellen?",
            ["Coordinaten invullen", "Teken op de afbeelding"],
            horizontal=True,
        )

        grid_x = grid_y = grid_w = grid_h = None

        if method == "Coordinaten invullen":
            st.markdown(
                "**Tip:** Designer met standaardinstellingen geeft: "
                "x=134, y=902, b=2211, h=2195"
            )
            col1, col2, col3, col4 = st.columns(4)
            grid_x = col1.number_input("X (links)", min_value=0, max_value=orig_w, value=min(134, orig_w))
            grid_y = col2.number_input("Y (boven)", min_value=0, max_value=orig_h, value=min(902, orig_h))
            grid_w = col3.number_input("Breedte", min_value=50, max_value=orig_w, value=min(2211, orig_w - 50))
            grid_h = col4.number_input("Hoogte", min_value=50, max_value=orig_h, value=min(2195, orig_h - 50))

            overlay = _draw_grid_overlay(bg, grid_x, grid_y, grid_w, grid_h)
            scale = min(700 / orig_w, 900 / orig_h)
            st.image(
                overlay.resize((int(orig_w * scale), int(orig_h * scale)), Image.LANCZOS),
                caption="Rasterpreview",
                width="content",
            )

        else:
            try:
                from streamlit_drawable_canvas import st_canvas
                MAX_W = 700
                scale = MAX_W / orig_w
                bg_display = bg.resize((MAX_W, int(orig_h * scale)), Image.LANCZOS)
                st.markdown("**Teken een rechthoek** rond het gebied waar het 5×5 raster moet komen.")
                canvas_result = st_canvas(
                    background_image=bg_display,
                    drawing_mode="rect",
                    stroke_color="#FF2200",
                    stroke_width=3,
                    fill_color="rgba(255, 34, 0, 0.08)",
                    height=int(orig_h * scale),
                    width=MAX_W,
                    key="grid_canvas",
                    update_streamlit=True,
                )
                if canvas_result.json_data and canvas_result.json_data.get("objects"):
                    rect = canvas_result.json_data["objects"][-1]
                    sx = rect.get("scaleX", 1)
                    sy = rect.get("scaleY", 1)
                    grid_x = int(rect["left"] / scale)
                    grid_y = int(rect["top"] / scale)
                    grid_w = int(rect["width"] * sx / scale)
                    grid_h = int(rect["height"] * sy / scale)
                    st.success(f"Rastergebied: x={grid_x}, y={grid_y}, breedte={grid_w}, hoogte={grid_h}")
            except ImportError:
                st.error("`streamlit-drawable-canvas` niet beschikbaar. Kies 'Coordinaten invullen'.")

        if grid_x is not None and grid_w and grid_h:
            st.markdown("---")
            design_name = st.text_input(
                "Naam voor dit design",
                value=uploaded.name.rsplit(".", 1)[0],
                key="des_name_upload",
            )
            if st.button("Design opslaan", type="primary", key="save_upload"):
                save_path = DESIGNS_DIR / uploaded.name
                bg.save(str(save_path))
                save_design(
                    name=design_name,
                    image_path=str(save_path),
                    grid_x=int(grid_x),
                    grid_y=int(grid_y),
                    grid_w=int(grid_w),
                    grid_h=int(grid_h),
                )
                st.success(f"Design **{design_name}** opgeslagen.")
                st.rerun()

# ── Saved designs ──────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Opgeslagen designs")

designs = list_designs()
if not designs:
    st.info("Nog geen designs opgeslagen.")
else:
    for d in designs:
        img_path = Path(d.image_path)
        img_w, img_h = (2480, 3508)
        if img_path.exists():
            with Image.open(img_path) as _im:
                img_w, img_h = _im.size

        coords_doubled = (d.grid_x + d.grid_w) > img_w * 1.1 or (d.grid_y + d.grid_h) > img_h * 1.1

        c1, c2, c3, c4 = st.columns([4, 2, 1, 1])
        c1.markdown(f"**{d.name}**  \n`x={d.grid_x}, y={d.grid_y}, b={d.grid_w}, h={d.grid_h}`")
        c2.caption(d.created_at.strftime("%d-%m-%Y"))
        if coords_doubled:
            if c3.button("Repareer ÷2", key=f"fix_des_{d.id}", type="primary",
                         help="Coördinaten lijken verdubbeld — klik om te halveren"):
                update_design_grid(d.id, d.grid_x // 2, d.grid_y // 2, d.grid_w // 2, d.grid_h // 2)
                st.success("Coördinaten gerepareerd.")
                st.rerun()
        else:
            c3.caption("✓ OK")
        if c4.button("Verwijder", key=f"del_des_{d.id}"):
            delete_design(d.id)
            st.rerun()

        if img_path.exists():
            with st.expander("Controleer design", expanded=False):
                tab_overlay, tab_sample = st.tabs(["Raster overlay", "Voorbeeldkaart"])

                with tab_overlay:
                    overlay = _draw_grid_overlay(
                        Image.open(img_path).convert("RGB"),
                        d.grid_x, d.grid_y, d.grid_w, d.grid_h,
                    )
                    disp_w = 600
                    disp_h = int(disp_w * img_h / img_w)
                    st.image(overlay.resize((disp_w, disp_h), Image.LANCZOS), width="content")
                    _cw, _ch = d.grid_w // 5, d.grid_h // 5
                    _ft = max(36, int(_ch * 0.12))
                    _fa = max(28, int(_ch * 0.09))
                    st.caption(
                        f"Celgrootte: **{_cw} × {_ch} px**  ·  "
                        f"Titelfont: **{_ft} px ({round(_ft*0.25)} pt)**  ·  "
                        f"Artiestfont: **{_fa} px ({round(_fa*0.25)} pt)**"
                    )
                    if coords_doubled:
                        st.error("Coördinaten lijken buiten het beeld te vallen — gebruik de Repareer ÷2 knop hierboven.")

                with tab_sample:
                    sc1, sc2, sc3 = st.columns(3)
                    font_scale = sc1.slider(
                        "Lettergrootte", 0.5, 2.0, float(d.font_scale), 0.05,
                        key=f"fs_{d.id}",
                        help="1.0 = standaard (~12pt titels bij A4 300dpi)",
                    )
                    separator = sc2.selectbox(
                        "Scheidingsteken",
                        [" — ", " · ", " / ", " | ", ""],
                        index=[" — ", " · ", " / ", " | ", ""].index(d.separator)
                              if d.separator in [" — ", " · ", " / ", " | ", ""] else 0,
                        key=f"sep_{d.id}",
                    )
                    title_align = sc3.radio(
                        "Uitlijning",
                        ["left", "center"],
                        index=0 if d.title_align == "left" else 1,
                        horizontal=True,
                        key=f"ta_{d.id}",
                    )

                    if st.button("Stijl opslaan", key=f"save_style_{d.id}"):
                        update_design_style(d.id, font_scale, separator, title_align)
                        st.success("Stijl opgeslagen.")
                        st.rerun()

                    playlists = list_playlists()
                    if not playlists:
                        st.info("Geen playlists beschikbaar — laad eerst een playlist via de Playlist pagina.")
                    else:
                        pl_options = {f"{p['name']} ({p['track_count']} nrs)": p for p in playlists}
                        chosen_pl_label = st.selectbox(
                            "Playlist voor preview",
                            list(pl_options.keys()),
                            key=f"prev_pl_{d.id}",
                        )
                        chosen_pl = pl_options[chosen_pl_label]
                        if st.button("Genereer voorbeeldkaart", key=f"prev_btn_{d.id}"):
                            pl_result = load_playlist(chosen_pl["id"])
                            if pl_result:
                                _, pl_tracks = pl_result
                                try:
                                    import random as _rnd
                                    sample_tracks = _rnd.sample(pl_tracks, min(24, len(pl_tracks)))
                                    while len(sample_tracks) < 24:
                                        sample_tracks += sample_tracks
                                    sample_tracks = sample_tracks[:24]
                                    bg_img = Image.open(img_path).convert("RGB")
                                    sample = render_card(
                                        background=bg_img,
                                        grid_rect=d.grid_rect,
                                        tracks=sample_tracks,
                                        show_cover_art=False,
                                        card_id="VOORBEELD",
                                        font_scale=font_scale,
                                        separator=separator,
                                        title_align=title_align,
                                    )
                                    disp_w = 600
                                    disp_h = int(disp_w * sample.height / sample.width)
                                    st.image(sample.resize((disp_w, disp_h), Image.LANCZOS), width="content")
                                except Exception as exc:
                                    st.error(f"Preview mislukt: {exc}")
                            else:
                                st.error("Playlist kon niet geladen worden.")
