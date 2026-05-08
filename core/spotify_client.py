import re
import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from core.models import Track


def _get_client() -> spotipy.Spotify:
    try:
        client_id = st.secrets["SPOTIFY_CLIENT_ID"]
        client_secret = st.secrets["SPOTIFY_CLIENT_SECRET"]
    except Exception:
        raise RuntimeError(
            "Spotify credentials ontbreken. Voeg SPOTIFY_CLIENT_ID en "
            "SPOTIFY_CLIENT_SECRET toe aan .streamlit/secrets.toml."
        )
    auth = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    return spotipy.Spotify(client_credentials_manager=auth)


def _extract_playlist_id(url_or_id: str) -> str:
    url_or_id = url_or_id.strip()
    # spotify:playlist:ID
    m = re.match(r"spotify:playlist:([A-Za-z0-9]+)", url_or_id)
    if m:
        return m.group(1)
    # https://open.spotify.com/playlist/ID?...
    m = re.match(r"https?://open\.spotify\.com/playlist/([A-Za-z0-9]+)", url_or_id)
    if m:
        return m.group(1)
    # raw ID (alphanumeric, 22 chars typically)
    if re.match(r"^[A-Za-z0-9]{10,}$", url_or_id):
        return url_or_id
    raise ValueError(f"Kan geen playlist-ID vinden in: {url_or_id!r}")


def _pick_cover(images: list[dict], preferred_size: int) -> str:
    if not images:
        return ""
    best = min(images, key=lambda img: abs((img.get("width") or 0) - preferred_size))
    return best.get("url", "")


def fetch_playlist(playlist_url: str) -> tuple[str, list[Track]]:
    """Returns (playlist_name, tracks). Handles pagination, filters local/unavailable."""
    sp = _get_client()
    playlist_id = _extract_playlist_id(playlist_url)

    try:
        meta = sp.playlist(playlist_id, fields="name,tracks.total")
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 404:
            raise ValueError("Playlist niet gevonden. Is de playlist openbaar?")
        raise

    playlist_name: str = meta["name"]
    tracks: list[Track] = []
    offset = 0
    limit = 100

    while True:
        page = sp.playlist_tracks(
            playlist_id,
            offset=offset,
            limit=limit,
            fields="items(track(id,name,artists,album(name,images),is_local,preview_url)),next",
        )
        items = page.get("items", [])
        if not items:
            break

        for item in items:
            raw = item.get("track")
            if not raw:
                continue
            if raw.get("is_local"):
                continue
            if not raw.get("id"):
                continue

            artists = raw.get("artists") or []
            artist_str = ", ".join(a["name"] for a in artists) if artists else "Onbekend"
            album = raw.get("album") or {}
            images = album.get("images") or []

            tracks.append(Track(
                spotify_id=raw["id"],
                title=raw.get("name", "Onbekend"),
                artist=artist_str,
                album=album.get("name", ""),
                cover_url_300=_pick_cover(images, 300),
                cover_url_64=_pick_cover(images, 64),
            ))

        if not page.get("next"):
            break
        offset += limit

    # Deduplicate by spotify_id (keep first occurrence)
    seen: set[str] = set()
    unique: list[Track] = []
    for t in tracks:
        if t.spotify_id not in seen:
            seen.add(t.spotify_id)
            unique.append(t)

    return playlist_name, unique
