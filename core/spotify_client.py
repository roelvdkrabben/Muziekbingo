import base64
import re
import time

import requests as _req
import spotipy

from core.models import Track


def _get_secrets() -> tuple[str, str, str]:
    """Returns (client_id, client_secret, refresh_token)."""
    try:
        import streamlit as st
        client_id = st.secrets["SPOTIFY_CLIENT_ID"]
        client_secret = st.secrets["SPOTIFY_CLIENT_SECRET"]
        refresh_token = st.secrets.get("SPOTIFY_REFRESH_TOKEN", "")
    except Exception:
        import os
        client_id = os.environ.get("SPOTIFY_CLIENT_ID", "")
        client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
        refresh_token = os.environ.get("SPOTIFY_REFRESH_TOKEN", "")

    if not client_id or not client_secret:
        raise RuntimeError(
            "Spotify credentials ontbreken. Voeg SPOTIFY_CLIENT_ID en "
            "SPOTIFY_CLIENT_SECRET toe aan .streamlit/secrets.toml."
        )
    if not refresh_token:
        raise RuntimeError(
            "SPOTIFY_REFRESH_TOKEN ontbreekt. Voer scripts/spotify_auth.py eenmalig uit "
            "en voeg het refresh token toe aan .streamlit/secrets.toml."
        )
    return client_id, client_secret, refresh_token


def _get_access_token() -> str:
    """Exchange stored refresh token for an access token. Cached ~55 min in session state."""
    try:
        import streamlit as st
        cache = st.session_state.get("_spotify_token_cache", {})
        if cache.get("expires_at", 0) > time.time():
            return cache["access_token"]
    except Exception:
        cache = {}

    client_id, client_secret, refresh_token = _get_secrets()
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = _req.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    token_cache = {
        "access_token": data["access_token"],
        "expires_at": time.time() + data.get("expires_in", 3600) - 60,
    }
    try:
        import streamlit as st
        st.session_state["_spotify_token_cache"] = token_cache
    except Exception:
        pass
    return data["access_token"]


def get_spotify_client() -> spotipy.Spotify:
    return spotipy.Spotify(auth=_get_access_token())


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
        meta = sp.playlist(playlist_id, fields="name")
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 404:
            raise ValueError("Playlist niet gevonden. Is de playlist openbaar?")
        if e.http_status == 403:
            raise ValueError("Toegang geweigerd (403). De playlist is privé.")
        raise

    playlist_name: str = meta["name"]
    tracks: list[Track] = []

    # Use the dedicated items endpoint; fall back to the older tracks endpoint.
    try:
        page = sp.playlist_items(playlist_id)
    except spotipy.exceptions.SpotifyException:
        page = sp.playlist_tracks(playlist_id)

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
        raise ValueError("Playlist bevat geen streambare nummers.")

    return playlist_name, unique
