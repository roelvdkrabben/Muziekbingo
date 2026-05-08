import io
from pathlib import Path

import streamlit as st
from PIL import Image

from app import check_password
from db.storage import init_db, save_design, list_designs, delete_design

try:
    from streamlit_drawable_canvas import st_canvas
    CANVAS_AVAILABLE = True
except ImportError:
    CANVAS_AVAILABLE = False

st.set_page_config(page_title="Design — MuziekBingo", layout="wide")
init_db()

if not check_password():
    st.stop()

DESIGNS_DIR = Path("data/designs")
DESIGNS_DIR.mkdir(parents=True, exist_ok=True)

st.title("Design uploaden")
st.caption(
    "Upload je achtergrondafbeelding (uit de MuziekBingo Background Designer of eigen ontwerp) "
    "en markeer het 5×5 rastergebied."
)

# ── Upload ─────────────────────────────────────────────────────────────────────
uploaded = st.file_uploader("Achtergrond uploaden (PNG of JPG)", type=["png", "jpg", "jpeg"])

if uploaded:
    bg = Image.open(uploaded).convert("RGB")
    orig_w, orig_h = bg.size

    st.info(f"Afbeelding: **{orig_w} × {orig_h} px**  "
            f"({'A4 300 DPI' if orig_w == 2480 and orig_h == 3508 else 'Let op: niet A4 300 DPI formaat'})")

    # ── Grid rect method ───────────────────────────────────────────────────────
    method = st.radio(
        "Hoe wil je het rastergebied instellen?",
        ["Teken op de afbeelding", "Coordinaten invullen"],
        horizontal=True,
    )

    grid_x = grid_y = grid_w = grid_h = None

    if method == "Coordinaten invullen":
        st.markdown(
            "**Tip:** Als je de MuziekBingo Background Designer gebruikt met standaard instellingen, "
            "zijn de coordinaten: x=134, y=902, b=2211, h=2195"
        )
        col1, col2, col3, col4 = st.columns(4)
        grid_x = col1.number_input("X (links)", min_value=0, max_value=orig_w, value=134)
        grid_y = col2.number_input("Y (boven)", min_value=0, max_value=orig_h, value=902)
        grid_w = col3.number_input("Breedte", min_value=50, max_value=orig_w, value=2211)
        grid_h = col4.number_input("Hoogte", min_value=50, max_value=orig_h, value=2195)

        # Preview with grid overlay
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
        preview_small = preview.resize((int(orig_w * scale), int(orig_h * scale)), Image.LANCZOS)
        st.image(preview_small, caption="Rasterpreview", use_container_width=False)

    else:
        if not CANVAS_AVAILABLE:
            st.error(
                "`streamlit-drawable-canvas` is niet geinstalleerd. "
                "Voer `pip install streamlit-drawable-canvas` uit of kies de coordinaten-methode."
            )
        else:
            MAX_DISPLAY_W = 700
            scale = MAX_DISPLAY_W / orig_w
            display_w = MAX_DISPLAY_W
            display_h = int(orig_h * scale)

            bg_display = bg.resize((display_w, display_h), Image.LANCZOS)

            st.markdown("**Teken een rechthoek** rond het gebied waar het 5×5 raster moet komen.")

            canvas_result = st_canvas(
                background_image=bg_display,
                drawing_mode="rect",
                stroke_color="#FF2200",
                stroke_width=3,
                fill_color="rgba(255, 34, 0, 0.08)",
                height=display_h,
                width=display_w,
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
                st.success(
                    f"Rastergebied: x={grid_x}, y={grid_y}, "
                    f"breedte={grid_w}, hoogte={grid_h}"
                )

    # ── Save ──────────────────────────────────────────────────────────────────
    if grid_x is not None and grid_w and grid_h:
        st.markdown("---")
        design_name = st.text_input("Naam voor dit design", value=uploaded.name.rsplit(".", 1)[0])
        if st.button("Design opslaan", type="primary"):
            save_path = DESIGNS_DIR / uploaded.name
            bg.save(str(save_path))
            design_id = save_design(
                name=design_name,
                image_path=str(save_path),
                grid_x=int(grid_x),
                grid_y=int(grid_y),
                grid_w=int(grid_w),
                grid_h=int(grid_h),
            )
            st.success(f"Design **{design_name}** opgeslagen (ID {design_id}).")
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
