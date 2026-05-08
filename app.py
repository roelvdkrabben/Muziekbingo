import base64
import hashlib
import streamlit as st
from pathlib import Path

from streamlit_cookies_controller import CookieController

from db.storage import init_db, list_playlists, list_designs, list_card_sets

_AUTH_COOKIE = "mb_auth"
_COOKIE_DAYS = 30

for d in ["data/designs", "data/exports", "data/covers", "assets/fonts"]:
    Path(d).mkdir(parents=True, exist_ok=True)

init_db()

st.set_page_config(
    page_title="MuziekBingo",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Cookie controller ──────────────────────────────────────────────────────────
_controller = CookieController()


def _get_cookie(name: str):
    """Safe read: returns None on first render before the component has initialised."""
    try:
        return _controller.get(name)
    except Exception:
        return None


def _auth_hash(password: str) -> str:
    return hashlib.sha256(f"muziekbingo-{password}".encode()).hexdigest()[:40]


def _render_sidebar_footer() -> None:
    logo_path = Path("assets/taigers-logo.png")
    if not logo_path.exists():
        return
    logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()
    st.sidebar.markdown(
        f"""<div style="position:fixed;bottom:16px;left:0;width:244px;
                        padding:0 20px;opacity:0.35;pointer-events:none;">
              <p style="margin:0 0 4px;font-size:10px;color:gray;
                        letter-spacing:.08em;">Made by</p>
              <img src="data:image/png;base64,{logo_b64}"
                   style="width:72px;filter:grayscale(1);" alt="Taigers"/>
            </div>""",
        unsafe_allow_html=True,
    )


def check_password() -> bool:
    if st.session_state.get("authenticated"):
        _render_sidebar_footer()
        return True

    try:
        app_password = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        app_password = ""

    if not app_password:
        st.session_state["authenticated"] = True
        return True

    # On the very first render the CookieController component hasn't sent its
    # data yet, so _get_cookie() returns None even when a valid cookie exists.
    # Stop here silently; the controller triggers a rerun and cookies are
    # available from the second render onward.
    if not st.session_state.get("_auth_initialized"):
        st.session_state["_auth_initialized"] = True
        st.stop()

    # Auto-login via cookie
    if app_password and _get_cookie(_AUTH_COOKIE) == _auth_hash(app_password):
        st.session_state["authenticated"] = True
        st.session_state["_goto_playlist"] = True
        return True

    st.markdown("## MuziekBingo — Inloggen")
    pwd = st.text_input("Wachtwoord", type="password", key="login_pwd")
    if st.button("Inloggen"):
        if pwd == app_password:
            st.session_state["authenticated"] = True
            _controller.set(_AUTH_COOKIE, _auth_hash(app_password), max_age=_COOKIE_DAYS * 86400)
            st.session_state["_goto_playlist"] = True
            st.rerun()
        else:
            st.error("Onjuist wachtwoord.")
    return False


if not check_password():
    st.stop()

if st.session_state.pop("_goto_playlist", False):
    st.switch_page("pages/1_Playlist.py")

st.title("MuziekBingo Generator")
st.caption("Genereer print-klare bingo-kaarten vanuit een Spotify-playlist.")

playlists = list_playlists()
designs = list_designs()
card_sets = list_card_sets()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Playlists opgeslagen", len(playlists))
with col2:
    st.metric("Designs opgeslagen", len(designs))
with col3:
    st.metric("Kaartsets gemaakt", len(card_sets))

st.markdown("---")
st.markdown("""
### Hoe werkt het?

1. **Playlist** — Plak een Spotify playlist-URL en haal de nummers op.
2. **Design** — Upload je achtergrondafbeelding en markeer waar het 5×5 raster komt.
3. **Genereer** — Kies playlist + design, stel het aantal kaarten in en exporteer als PDF of PNG.
4. **Bibliotheek** — Bekijk en herdownload eerder gemaakte sets.
""")

with st.expander("Hoe werkt de kaartgeneratie?", expanded=False):
    st.markdown("""
### Hoe worden de bingo-kaarten gegenereerd?

Elke kaart heeft 25 vakjes: een 5×5 raster met een gratis vakje in het midden. De overige 24 vakjes worden
gevuld met willekeurige nummers uit je Spotify-playlist. Over alle kaarten heen zijn **geen twee kaarten
identiek**, maar ze delen wel nummers — dat is wiskundig onvermijdelijk als je veel kaarten maakt van een
beperkte playlist.

De tool probeert **overlap te minimaliseren**: per kaart worden 100 kandidaatcombinaties gegenereerd en
wordt de combinatie gekozen die de minste nummers deelt met alle eerder gemaakte kaarten.

---

### Hoeveel nummers heb ik nodig?

| Nummers in playlist | Resultaat |
|---|---|
| < 50 | Niet gebruiken — te veel overlap |
| 50 – 74 | Werkbaar voor tot 30 kaarten, maar overlappende bingo's zijn waarschijnlijk |
| 75 – 99 | Goed voor tot 100 kaarten |
| 100 – 149 | Uitstekend voor tot 200 kaarten |
| 150+ | Ideaal — minimale overlap, ook bij 200+ kaarten |

**Vuistregel:** streef naar minimaal **3x het aantal kaarten** aan playlist-nummers, minimaal 75 nummers.

---

### Tips voor het beste resultaat

- **Gevarieerde playlist:** vermijd remixes of meerdere versies van hetzelfde nummer.
- **Test met een kleine batch eerst:** genereer 5 kaarten, check de opmaak, genereer daarna de volledige set.
- **Gebruik de seed:** dezelfde seed + playlist + design = exact dezelfde kaarten. Sla hem op voor herdrukken.
- **Cover art is inkt-intensief:** zet het uit bij zwart-wit printen.
- **Kaarten per pagina:** 1 per A4 voor premium events; 2 per A4 met snijlijn is de sweet spot bij 100+ kaarten.

---

### Wat krijg ik na het genereren?

- Een PDF met alle kaarten (1, 2 of 4 per A4) of een ZIP met losse PNG-bestanden per kaart.
- Een DJ-checklist achteraan de PDF: per kaart-ID de 24 nummers in volgorde.
- Overlap-statistieken in de app: maximale en gemiddelde overlap.

---

### Set hergebruiken

Elke set is opgeslagen in de Bibliotheek met seed:
- Dezelfde kaarten opnieuw printen: klik "Re-exporteer PDF" in de Bibliotheek.
- Nieuwe batch, zelfde playlist en design: klik "Genereer met nieuwe seed".
""")
