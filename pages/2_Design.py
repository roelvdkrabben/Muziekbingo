import base64
import io
from pathlib import Path

import streamlit as st
from PIL import Image

from app import check_password
from db.storage import init_db, save_design, list_designs, delete_design
from designer_component import designer_component

st.set_page_config(page_title="Design — MuziekBingo", layout="wide")
init_db()

if not check_password():
    st.stop()

DESIGNS_DIR = Path("data/designs")
DESIGNS_DIR.mkdir(parents=True, exist_ok=True)

st.title("Design")

tab_designer, tab_upload = st.tabs(["Designer", "Upload eigen PNG"])

# ── Tab 1: Embedded designer ───────────────────────────────────────────────────
with tab_designer:

    # Save form — shown at the TOP when a result is pending, so user always sees it
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
            # grid_rect comes from computeGridRect() which works in full PAGE coords (2480×3508)
            # The image is transported at 50% but coords are already full-res — use as-is
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
                # Upscale the 50%-res JPEG back to full A4 resolution
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

    # Debug: show what the component returned
    if result is not None:
        st.caption(f"Component waarde ontvangen — png: {'ja' if result.get('png_base64') else 'nee'}, grid: {result.get('grid_rect')}")

    # Store new result in session_state and rerun so the form renders at the top
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
            grid_x = col1.number_input("X (links)", min_value=0, max_value=orig_w, value=134)
            grid_y = col2.number_input("Y (boven)", min_value=0, max_value=orig_h, value=902)
            grid_w = col3.number_input("Breedte", min_value=50, max_value=orig_w, value=2211)
            grid_h = col4.number_input("Hoogte", min_value=50, max_value=orig_h, value=2195)

            preview = bg.copy()
            from PIL import ImageDraw
            draw = ImageDraw.Draw(preview)
            for row in range(6):
                y = grid_y + row * (grid_h // 5)
                draw.line([(grid_x, y), (grid_x + grid_w, y)], fill=(200, 50, 50), width=8)
            for col in range(6):
                x = grid_x + col * (grid_w // 5)
                draw.line([(x, grid_y), (x, grid_y + grid_h)], fill=(200, 50, 50), width=8)
            scale = min(700 / orig_w, 900 / orig_h)
            st.image(
                preview.resize((int(orig_w * scale), int(orig_h * scale)), Image.LANCZOS),
                caption="Rasterpreview",
                use_container_width=False,
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
        c1, c2, c3 = st.columns([4, 2, 1])
        c1.markdown(f"**{d.name}**  \n`x={d.grid_x}, y={d.grid_y}, b={d.grid_w}, h={d.grid_h}`")
        c2.caption(d.created_at.strftime("%d-%m-%Y"))
        if c3.button("Verwijder", key=f"del_des_{d.id}"):
            delete_design(d.id)
            st.rerun()

        img_path = Path(d.image_path)
        if img_path.exists():
            with st.expander("Bekijk", expanded=False):
                thumb = Image.open(img_path).resize((400, int(400 * 3508 / 2480)), Image.LANCZOS)
                st.image(thumb)
