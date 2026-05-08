import re
import streamlit as st

from app import check_password, clear_spotify_token, save_spotify_token
from core.spotify_client import (
    fetch_playlist,
    get_auth_url,
    exchange_code,
    _extract_playlist_id,
)
from db.storage import init_db, save_playlist, list_playlists, delete_playlist, load_playlist

st.set_page_config(page_title="Playlist — MuziekBingo", layout="wide")
init_db()

if not check_password():
    st.stop()

st.title("Playlist ophalen")

# ── Login-status ───────────────────────────────────────────────────────────────
token = st.session_state.get("spotify_token")

if not token:
    # Automatisch afvangen als Spotify terugstuurde naar deze pagina
    auto_code = st.query_params.get("code")
    if auto_code:
        with st.spinner("Spotify-account koppelen…"):
            try:
                token_info = exchange_code(auto_code)
                st.session_state["spotify_token"] = token_info
                save_spotify_token(token_info)
                st.query_params.clear()
                st.rerun()
            except Exception as exc:
                st.error(f"Koppeling mislukt: {exc}")
                st.query_params.clear()
        st.stop()

    st.markdown("### Stap 1 — Koppel je Spotify-account")

    auth_url = get_auth_url()

    st.markdown(
        "Klik op de knop hieronder. Je wordt naar Spotify gestuurd en daarna automatisch "
        "teruggeleid naar deze pagina."
    )

    # target="_self" zorgt dat de redirect in hetzelfde tabblad blijft
    st.markdown(
        f'<a href="{auth_url}" target="_self" style="display:inline-block;padding:0.45em 1.1em;'
        'background:#1DB954;color:#fff;border-radius:0.4em;text-decoration:none;font-weight:600;">'
        'Openen: Spotify-autorisatie</a>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("**Werkt de automatische omleiding niet?** Plak de URL hieronder:")
    callback_url = st.text_input(
        "Volledige callback-URL uit je adresbalk:",
        placeholder="https://muziekbingo.streamlit.app?code=AQC...",
    )
    if st.button("Koppelen", type="primary", disabled=not callback_url):
        m = re.search(r"[?&]code=([^&]+)", callback_url)
        if m:
            with st.spinner("Spotify-account koppelen…"):
                try:
                    token_info = exchange_code(m.group(1))
                    st.session_state["spotify_token"] = token_info
                    save_spotify_token(token_info)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Koppeling mislukt: {exc}")
        else:
            st.error("Geen `code=` gevonden in de URL. Controleer of je de volledige URL hebt geplakt.")
    st.stop()

# ── Spotify gekoppeld ─────────────────────────────────────────────────────────
col_ok, col_uit = st.columns([4, 1])
col_ok.success("Spotify gekoppeld")
if col_uit.button("Ontkoppelen"):
    del st.session_state["spotify_token"]
    clear_spotify_token()
    st.rerun()

st.markdown("---")

# ── Playlist ophalen ──────────────────────────────────────────────────────────
with st.form("playlist_form"):
    url = st.text_input(
        "Spotify playlist-URL",
        placeholder="https://open.spotify.com/playlist/...",
        help="Werkt met openbare en privé-playlists waar je toegang toe hebt.",
    )
    submitted = st.form_submit_button("Haal nummers op")

if submitted and url.strip():
    with st.spinner("Nummers ophalen van Spotify…"):
        try:
            name, tracks = fetch_playlist(url.strip())
            try:
                playlist_id = _extract_playlist_id(url.strip())
            except ValueError:
                playlist_id = url.strip()
            save_playlist(playlist_id, name, tracks)
            st.success(f"**{name}** opgeslagen — {len(tracks)} nummers.")

            with st.expander(f"Bekijk nummers ({len(tracks)})", expanded=True):
                rows = [{"#": i + 1, "Titel": t.title, "Artiest": t.artist, "Album": t.album}
                        for i, t in enumerate(tracks)]
                st.dataframe(rows, use_container_width=True, hide_index=True)
        except RuntimeError as exc:
            if "niet_geauthenticeerd" in str(exc):
                st.error("Sessie verlopen — koppel je Spotify-account opnieuw.")
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
        if c4.button("Verwijder", key=f"del_pl_{p['id']}"):
            delete_playlist(p["id"])
            st.rerun()

        with st.expander("Bekijk nummers", expanded=False):
            result = load_playlist(p["id"])
            if result:
                _, tracks = result
                rows = [{"#": i + 1, "Titel": t.title, "Artiest": t.artist}
                        for i, t in enumerate(tracks)]
                st.dataframe(rows, use_container_width=True, hide_index=True)
