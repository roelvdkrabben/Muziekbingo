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

    st.info(
        "**Hoe het werkt:**\n"
        "1. Klik op de knop hieronder — Spotify opent in een nieuw tabblad\n"
        "2. Log in en klik op **Akkoord**\n"
        "3. Je browser toont een foutpagina ('localhost heeft de verbinding geweigerd') — **dat is normaal**\n"
        "4. Kopieer de volledige URL uit de adresbalk (begint met `https://localhost?code=...`)\n"
        "5. Kom terug naar dit tabblad, plak de URL hieronder en klik **Koppelen**"
    )

    st.link_button("Openen: Spotify-autorisatie", auth_url, type="primary")

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

# ── Diagnose ──────────────────────────────────────────────────────────────────
with st.expander("Diagnose (ruwe API-response)", expanded=False):
    diag_url = st.text_input(
        "Playlist-URL voor diagnose",
        placeholder="https://open.spotify.com/playlist/...",
        key="diag_url",
    )
    if st.button("Toon ruwe API-data", key="diag_btn"):
        import requests as _req
        try:
            from core.spotify_client import get_spotify_client, _extract_playlist_id
            sp = get_spotify_client()
            pid = _extract_playlist_id(diag_url.strip())
            token_info = st.session_state.get("spotify_token", {})
            access_token = token_info.get("access_token", "")

            st.markdown("**1. sp.playlist() (spotipy)**")
            data = sp.playlist(pid)
            tr = data.get("tracks") or {}
            items = tr.get("items") or []
            st.write({
                "naam": data.get("name"),
                "tracks.total": tr.get("total"),
                "tracks.next": tr.get("next"),
                "aantal_items": len(items),
            })

            st.markdown("**2. GET /playlists/{id}/tracks (directe HTTP)**")
            r = _req.get(
                f"https://api.spotify.com/v1/playlists/{pid}/tracks",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"limit": 3},
            )
            st.write({"status": r.status_code, "body": r.json()})

            st.markdown("**3. GET /playlists/{id}/items (directe HTTP)**")
            r2 = _req.get(
                f"https://api.spotify.com/v1/playlists/{pid}/items",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"limit": 3},
            )
            st.write({"status": r2.status_code, "body": r2.json()})

            st.write({"token_scope": token_info.get("scope")})
        except Exception as exc:
            st.error(f"Diagnose fout: {exc}")

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
