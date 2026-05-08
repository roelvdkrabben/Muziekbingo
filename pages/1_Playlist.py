import streamlit as st

from app import check_password
from core.spotify_client import fetch_playlist, get_spotify_client, _extract_playlist_id
from db.storage import init_db, save_playlist, list_playlists, delete_playlist, load_playlist

st.set_page_config(page_title="Playlist — MuziekBingo", layout="wide")
init_db()

if not check_password():
    st.stop()

st.title("Playlist ophalen")

# ── Playlist ophalen ──────────────────────────────────────────────────────────
with st.form("playlist_form"):
    url = st.text_input(
        "Spotify playlist-URL",
        placeholder="https://open.spotify.com/playlist/...",
        help="Werkt met alle openbare Spotify-playlists.",
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
            sp = get_spotify_client()
            pid = _extract_playlist_id(diag_url.strip())

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
            token = sp.auth_manager.get_access_token(as_dict=False)
            r = _req.get(
                f"https://api.spotify.com/v1/playlists/{pid}/tracks",
                headers={"Authorization": f"Bearer {token}"},
                params={"limit": 3},
            )
            st.write({"status": r.status_code, "body": r.json()})

            st.markdown("**3. GET /playlists/{id}/items (directe HTTP)**")
            r2 = _req.get(
                f"https://api.spotify.com/v1/playlists/{pid}/items",
                headers={"Authorization": f"Bearer {token}"},
                params={"limit": 3},
            )
            st.write({"status": r2.status_code, "body": r2.json()})
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
