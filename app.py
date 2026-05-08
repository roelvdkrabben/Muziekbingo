import streamlit as st
from pathlib import Path

from db.storage import init_db, list_playlists, list_designs, list_card_sets

# ── Bootstrap ──────────────────────────────────────────────────────────────────
for d in ["data/designs", "data/exports", "data/covers", "assets/fonts"]:
    Path(d).mkdir(parents=True, exist_ok=True)

init_db()

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MuziekBingo",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Spotify OAuth callback (altijd op de root afhandelen) ──────────────────────
# Spotify stuurt de gebruiker terug naar de root URL met ?code=...
# Dit loopt vóór check_password zodat de redirect niet geblokkeerd wordt.
_params = st.query_params
if "code" in _params and "spotify_token" not in st.session_state:
    with st.spinner("Spotify-account koppelen…"):
        try:
            from core.spotify_client import exchange_code
            token_info = exchange_code(_params["code"])
            st.session_state["spotify_token"] = token_info
            st.query_params.clear()
            st.switch_page("pages/1_📥_Playlist.py")
        except Exception as exc:
            st.error(f"Spotify koppeling mislukt: {exc}")
            st.query_params.clear()

# ── App-wachtwoord ─────────────────────────────────────────────────────────────

def check_password() -> bool:
    """Returns True when the user is authenticated (or no password is set)."""
    if st.session_state.get("authenticated"):
        return True

    try:
        app_password = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        app_password = ""

    if not app_password:
        st.session_state["authenticated"] = True
        return True

    st.markdown("## 🔐 MuziekBingo — Inloggen")
    pwd = st.text_input("Wachtwoord", type="password", key="login_pwd")
    if st.button("Inloggen"):
        if pwd == app_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Onjuist wachtwoord.")
    return False


if not check_password():
    st.stop()

# ── Home page ──────────────────────────────────────────────────────────────────
st.title("🎵 MuziekBingo Generator")
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

1. **📥 Playlist** — Koppel je Spotify-account en haal een playlist op.
2. **🎨 Design** — Upload je achtergrondafbeelding en markeer waar het 5×5 raster komt.
3. **🎲 Genereer** — Kies playlist + design, stel het aantal kaarten in en exporteer als **PDF** of **PNG (ZIP)**.
4. **📚 Bibliotheek** — Bekijk en herdownload eerder gemaakte sets.
""")

with st.expander("ℹ️ Hoe werkt de kaartgeneratie?", expanded=False):
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
| < 50 | ❌ Niet gebruiken — te veel overlap |
| 50 – 74 | ⚠️ Werkbaar voor ≤ 30 kaarten, maar overlappende bingo's waarschijnlijk |
| 75 – 99 | ✅ Goed voor tot 100 kaarten |
| 100 – 149 | ✅ Uitstekend voor tot 200 kaarten |
| 150+ | 🎯 Ideaal — minimale overlap, ook bij 200+ kaarten |

**Vuistregel:** streef naar minimaal **3× het aantal kaarten** aan playlist-nummers, minimaal 75 nummers.

---

### Tips voor het beste resultaat

- **Gevarieerde playlist:** vermijd remixes/meerdere versies van hetzelfde nummer.
- **Test met een kleine batch eerst:** genereer 5 kaarten, check de opmaak, genereer daarna de volledige set.
- **Gebruik de seed:** dezelfde seed + playlist + design = exact dezelfde kaarten. Sla hem op voor herdrukken.
- **Cover art is inkt-intensief:** zet het uit bij zwart-wit printen.
- **Kaarten per pagina:** 1/A4 voor premium events; 2/A4 met snijlijn is de sweet spot bij 100+ kaarten; 4/A4 alleen als je design groot genoeg is om klein te zijn.

---

### Wat krijg ik na het genereren?

- **Eén PDF** met alle kaarten (1/2/4 per A4) óf een **ZIP met losse PNG-bestanden** per kaart.
- **DJ-checklist** (in de PDF): per kaart-ID de 24 nummers in volgorde.
- **Overlap-statistieken** in de app: maximale en gemiddelde overlap.

---

### Set hergebruiken

Elke set is opgeslagen in de Bibliotheek met seed:
- **Dezelfde kaarten opnieuw printen** → 'Re-exporteer PDF' in de Bibliotheek.
- **Nieuwe batch, zelfde playlist + design** → 'Genereer met nieuwe seed'.
""")
