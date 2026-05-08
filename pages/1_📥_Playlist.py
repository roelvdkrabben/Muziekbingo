import streamlit as st

from app import check_password
from core.spotify_client import (
    fetch_playlist,
    get_auth_url,
    exchange_code,
    _extract_playlist_id,
)
from db.storage import init_db, save_playlist, list_playlists, delete_playlist, load_playlist

st.set_page_config(page_title="Playlist — MuziekBingo", page_icon="📥", layout="wide")
init_db()

if not check_password():
    st.stop()

st.title("📥 Playlist ophalen")

# ── Stap 1: OAuth callback afhandelen ─────────────────────────────────────────
# Spotify stuurt de gebruiker terug naar deze pagina met ?code=...
params = st.query_params
if "code" in params and "spotify_token" not in st.session_state:
    with st.spinner("Spotify-account koppelen…"):
        try:
            token_info = exchange_code(params["code"])
            st.session_state["spotify_token"] = token_info
            st.query_params.clear()          # haal de code uit de URL
            st.rerun()
        except Exception as exc:
            st.error(f"Spotify koppeling mislukt: {exc}")
            st.query_params.clear()

# ── Stap 2: Login-status tonen ────────────────────────────────────────────────
token = st.session_state.get("spotify_token")

if not token:
    st.info(
        "Koppel eerst je Spotify-account. Klik op de knop hieronder — je wordt "
        "doorgestuurd naar Spotify en daarna automatisch teruggebracht."
    )
    auth_url = get_auth_url()
    st.link_button("🎵 Inloggen met Spotify", auth_url, type="primary")

    # ── Handmatige fallback (als redirect niet werkt) ──────────────────────────
    with st.expander("Werkt de knop niet? Handmatig de code invoeren"):
        st.markdown(
            f"1. Open deze URL: [{auth_url}]({auth_url})\n"
            "2. Autoriseer de app bij Spotify\n"
            "3. Je wordt doorgestuurd naar een pagina die mogelijk niet laadt — **kopieer de volledige URL** uit de adresbalk\n"
            "4. Plak die URL hieronder"
        )
        callback_url = st.text_input("Callback URL (begint met http://localhost...)")
        if st.button("Koppelen") and callback_url:
            import re
            m = re.search(r"[?&]code=([^&]+)", callback_url)
            if m:
                try:
                    token_info = exchange_code(m.group(1))
                    st.session_state["spotify_token"] = token_info
                    st.rerun()
                except Exception as exc:
                    st.error(f"Koppeling mislukt: {exc}")
            else:
                st.error("Geen 'code' gevonden in de URL.")
    st.stop()

# ── Spotify gekoppeld ─────────────────────────────────────────────────────────
st.success("✅ Spotify gekoppeld")
if st.button("Ontkoppelen"):
    del st.session_state["spotify_token"]
    st.rerun()

st.markdown("---")
st.caption("Plak een Spotify-playlist URL om nummers op te halen en op te slaan.")

# ── Playlist ophalen ──────────────────────────────────────────────────────────
with st.form("playlist_form"):
    url = st.text_input(
        "Spotify playlist-URL",
        placeholder="https://open.spotify.com/playlist/...",
        help="Werkt met openbare én privé-playlists waar je toegang tot hebt.",
    )
    submitted = st.form_submit_button("🎵 Haal nummers op")

if submitted and url.strip():
    with st.spinner("Nummers ophalen van Spotify…"):
        try:
            name, tracks = fetch_playlist(url.strip())
            try:
                playlist_id = _extract_playlist_id(url.strip())
            except ValueError:
                playlist_id = url.strip()
            save_playlist(playlist_id, name, tracks)
            st.success(f"✅ **{name}** opgeslagen — {len(tracks)} nummers.")

            with st.expander(f"Bekijk nummers ({len(tracks)})", expanded=False):
                rows = [{"#": i + 1, "Titel": t.title, "Artiest": t.artist, "Album": t.album}
                        for i, t in enumerate(tracks)]
                st.dataframe(rows, use_container_width=True, hide_index=True)
        except RuntimeError as exc:
            if "niet_geauthenticeerd" in str(exc):
                st.error("Sessie verlopen — log opnieuw in met Spotify.")
                del st.session_state["spotify_token"]
                st.rerun()
            else:
                st.error(f"Fout: {exc}")
        except Exception as exc:
            st.error(f"Fout: {exc}")

# ── Opgeslagen playlists ──────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Opgeslagen playlists")

saved = list_playlists()
if not saved:
    st.info("Nog geen playlists opgeslagen.")
else:
    for p in saved:
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        c1.markdown(f"**{p['name']}**")
        c2.caption(f"{p['track_count']} nummers")
        c3.caption(p["fetched_at"][:10])
        if c4.button("🗑 Verwijder", key=f"del_pl_{p['id']}"):
            delete_playlist(p["id"])
            st.rerun()

        with st.expander("Bekijk nummers", expanded=False):
            result = load_playlist(p["id"])
            if result:
                _, tracks = result
                rows = [{"#": i + 1, "Titel": t.title, "Artiest": t.artist}
                        for i, t in enumerate(tracks)]
                st.dataframe(rows, use_container_width=True, hide_index=True)
