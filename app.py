import hashlib
import json
import streamlit as st
from pathlib import Path

from streamlit_cookies_controller import CookieController

from db.storage import init_db, list_playlists, list_designs, list_card_sets

_AUTH_COOKIE = "mb_auth"
_TOKEN_COOKIE = "mb_spotify"
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


def save_spotify_token(token_info: dict) -> None:
    _controller.set(_TOKEN_COOKIE, json.dumps(token_info), max_age=_COOKIE_DAYS * 86400)


def clear_spotify_token() -> None:
    _controller.remove(_TOKEN_COOKIE)


def check_password() -> bool:
    """Authenticates the user; also restores Spotify token from cookie if needed."""

    # Restore Spotify token on every page load
    if "spotify_token" not in st.session_state:
        token_json = _get_cookie(_TOKEN_COOKIE)
        if token_json:
            try:
                st.session_state["spotify_token"] = json.loads(token_json)
            except Exception:
                pass

    if st.session_state.get("authenticated"):
        return True

    try:
        app_password = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        app_password = ""

    if not app_password:
        st.session_state["authenticated"] = True
        return True

    # Auto-login via cookie
    if app_password and _get_cookie(_AUTH_COOKIE) == _auth_hash(app_password):
        st.session_state["authenticated"] = True
        return True

    st.markdown("## MuziekBingo — Inloggen")
    if "spotify_token" in st.session_state:
        st.info("Spotify is al gekoppeld. Vul je wachtwoord in om verder te gaan.")
    pwd = st.text_input("Wachtwoord", type="password", key="login_pwd")
    if st.button("Inloggen"):
        if pwd == app_password:
            st.session_state["authenticated"] = True
            _controller.set(_AUTH_COOKIE, _auth_hash(app_password), max_age=_COOKIE_DAYS * 86400)
            st.rerun()
        else:
            st.error("Onjuist wachtwoord.")
    return False


# ── Intercept Spotify callback ─────────────────────────────────────────────────
_spotify_code = st.query_params.get("code")
if _spotify_code and "spotify_token" not in st.session_state:
    try:
        from core.spotify_client import exchange_code as _exchange_code
        _token_info = _exchange_code(_spotify_code)
        st.session_state["spotify_token"] = _token_info
        _controller.set(_TOKEN_COOKIE, json.dumps(_token_info), max_age=_COOKIE_DAYS * 86400)
        st.session_state["_goto_playlist"] = True
    except Exception as _exc:
        st.session_state["_spotify_error"] = str(_exc)
    st.query_params.clear()
    st.rerun()


if not check_password():
    st.stop()

if st.session_state.pop("_goto_playlist", False):
    st.switch_page("pages/1_Playlist.py")

if "_spotify_error" in st.session_state:
    st.error(f"Spotify koppeling mislukt: {st.session_state.pop('_spotify_error')}")

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

1. **Playlist** — Koppel je Spotify-account en haal een playlist op.
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
