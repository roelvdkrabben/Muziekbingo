import re

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from core.models import Track


def _get_secrets() -> tuple[str, str]:
    """Returns (client_id, client_secret)."""
    try:
        import streamlit as st
        client_id = st.secrets["SPOTIFY_CLIENT_ID"]
        client_secret = st.secrets["SPOTIFY_CLIENT_SECRET"]
    except Exception:
        import os
        client_id = os.environ.get("SPOTIFY_CLIENT_ID", "")
        client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        raise RuntimeError(
            "Spotify credentials ontbreken. Voeg SPOTIFY_CLIENT_ID en "
            "SPOTIFY_CLIENT_SECRET toe aan .streamlit/secrets.toml."
        )
    return client_id, client_secret


def get_spotify_client() -> spotipy.Spotify:
    """Get a Spotify client using Client Credentials (no user login required)."""
    client_id, client_secret = _get_secrets()
    auth = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    return spotipy.Spotify(auth_manager=auth)


def _extract_playlist_id(url_or_id: str) -> str:
    url_or_id = url_or_id.strip()
    m = re.match(r"spotify:playlist:([A-Za-z0-9]+)", url_or_id)
    if m:
        return m.group(1)
    m = re.match(r"https?://open\.spotify\.com/playlist/([A-Za-z0-9]+)", url_or_id)
    if m:
        return m.group(1)
    if re.match(r"^[A-Za-z0-9]{10,}$", url_or_id):
        return url_or_id
    raise ValueError(f"Kan geen playlist-ID vinden in: {url_or_id!r}")


def _pick_cover(images: list[dict], preferred_size: int) -> str:
    if not images:
        return ""
    best = min(images, key=lambda img: abs((img.get("width") or 0) - preferred_size))
    return best.get("url", "")


def _parse_track_item(item: dict) -> Track | None:
    # Feb 2026: Spotify renamed "track" → "item" in playlist item objects
    raw = item.get("item") or item.get("track")
    if not raw or raw.get("is_local") or not raw.get("id"):
        return None
    if raw.get("type") == "episode":
        return None
    artists = raw.get("artists") or []
    artist_str = ", ".join(a["name"] for a in artists) if artists else "Onbekend"
    album = raw.get("album") or {}
    images = album.get("images") or []
    return Track(
        spotify_id=raw["id"],
        title=raw.get("name", "Onbekend"),
        artist=artist_str,
        album=album.get("name", ""),
        cover_url_300=_pick_cover(images, 300),
        cover_url_64=_pick_cover(images, 64),
    )


def fetch_playlist(playlist_url: str) -> tuple[str, list[Track]]:
    """Returns (playlist_name, tracks)."""
    sp = get_spotify_client()
    playlist_id = _extract_playlist_id(playlist_url)

    try:
        data = sp.playlist(playlist_id)
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 404:
            raise ValueError("Playlist niet gevonden. Is de playlist openbaar?")
        if e.http_status == 403:
            raise ValueError("Toegang geweigerd (403). De playlist is privé.")
        raise

    playlist_name: str = data["name"]
    tracks: list[Track] = []

    # Feb 2026: Spotify renamed "tracks" → "items" in GET /playlists/{id} response.
    page = data.get("items") or data.get("tracks") or {}
    while page:
        for item in page.get("items") or []:
            t = _parse_track_item(item)
            if t:
                tracks.append(t)
        try:
            page = sp.next(page) if page.get("next") else None
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status in (403, 404):
                break
            raise

    seen: set[str] = set()
    unique: list[Track] = []
    for t in tracks:
        if t.spotify_id not in seen:
            seen.add(t.spotify_id)
            unique.append(t)

    if not unique:
        page0 = data.get("items") or data.get("tracks") or {}
        total = page0.get("total", 0)
        if total:
            raise ValueError(
                f"Playlist heeft {total} nummers maar geen kon worden geladen. "
                "Probeer het nogmaals."
            )
        raise ValueError("Playlist bevat geen streambare nummers.")

    return playlist_name, unique
