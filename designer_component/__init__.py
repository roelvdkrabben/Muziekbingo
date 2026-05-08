import streamlit.components.v1 as components
from pathlib import Path

_FRONTEND = Path(__file__).parent / "frontend"

designer_component = components.declare_component(
    "designer_component",
    path=str(_FRONTEND),
)
