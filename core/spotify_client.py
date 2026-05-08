import re

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from core.models import Track

SCOPE = "playlist-read-private playlist-read-collaborative"


def _get_secrets() -> tuple[str, str, str]:
    """Returns (client_id, client_secret, redirect_uri)."""
    try:
        import streamlit as st
        client_id = st.secrets["SPOTIFY_CLIENT_ID"]
        client_secret = st.secrets["SPOTIFY_CLIENT_SECRET"]
        redirect_uri = st.secrets.get("SPOTIFY_REDIRECT_URI", "http://localhost:8501")
    except Exception:
        import os
        client_id = os.environ.get("SPOTIFY_CLIENT_ID", "")
        client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
        redirect_uri = os.environ.get("SPOTIFY_REDIRECT_URI", "http://localhost:8501")

    if not client_id or not client_secret:
        raise RuntimeError(
            "Spotify credentials ontbreken. Voeg SPOTIFY_CLIENT_ID en "
            "SPOTIFY_CLIENT_SECRET toe aan .streamlit/secrets.toml."
        )
    return client_id, client_secret, redirect_uri


def get_auth_url() -> str:
    """Return the Spotify authorization URL to send the user to."""
    client_id, client_secret, redirect_uri = _get_secrets()
    auth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SCOPE,
        cache_path=None,
        open_browser=False,
    )
    return auth.get_authorize_url()


def exchange_code(code: str) -> dict:
    """Exchange authorization code for token_info dict."""
    client_id, client_secret, redirect_uri = _get_secrets()
    auth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SCOPE,
        cache_path=None,
        open_browser=False,
    )
    return auth.get_access_token(code, as_dict=True, check_cache=False)


def _get_client_from_token(token_info: dict) -> spotipy.Spotify:
    """Build a Spotify client from a stored token_info, refreshing if needed."""
    client_id, client_secret, redirect_uri = _get_secrets()
    auth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SCOPE,
        cache_path=None,
        open_browser=False,
    )
    if auth.is_token_expired(token_info):
        token_info = auth.refresh_access_token(token_info["refresh_token"])
        try:
            import streamlit as st
            st.session_state["spotify_token"] = token_info
        except Exception:
            pass

    return spotipy.Spotify(auth=token_info["access_token"])


def get_spotify_client() -> spotipy.Spotify:
    """Get Spotify client from the session token. Raises if not authenticated."""
    try:
        import streamlit as st
        token_info = st.session_state.get("spotify_token")
    except Exception:
        token_info = None

    if not token_info:
        raise RuntimeError("spotify_niet_geauthenticeerd")

    return _get_client_from_token(token_info)


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


def fetch_playlist(playlist_url: str) -> tuple[str, list[Track]]:
    """Returns (playlist_name, tracks). Fetches metadata and tracks separately."""
    sp = get_spotify_client()
    playlist_id = _extract_playlist_id(playlist_url)

    # Metadata only — this endpoint is not restricted in Development Mode
    try:
        meta = sp.playlist(playlist_id, fields="name,tracks.total")
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 404:
            raise ValueError("Playlist niet gevonden. Is de playlist openbaar?")
        if e.http_status == 403:
            raise ValueError(
                "Toegang geweigerd (403). Controleer in het Spotify Developer Dashboard of "
                "jouw Spotify-account is toegevoegd onder 'Users and Access'. "
                "In Development Mode mogen maximaal 25 gebruikers de app gebruiken."
            )
        raise

    playlist_name: str = meta["name"]
    total_in_playlist: int = (meta.get("tracks") or {}).get("total", 0)
    tracks: list[Track] = []

    # Tracks via /playlists/{id}/tracks (older endpoint, not /items)
    offset = 0
    limit = 100
    while True:
        try:
            page = sp.playlist_tracks(
                playlist_id,
                limit=limit,
                offset=offset,
                market="from_token",
            )
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 403:
                raise ValueError(
                    "Toegang geweigerd op /tracks (403). Controleer of jouw Spotify-account "
                    "is toegevoegd onder 'Users and Access' in het Spotify Developer Dashboard."
                )
            raise

        items = page.get("items") or []
        if not items:
            break

        for item in items:
            raw = item.get("track")
            if not raw or raw.get("is_local") or not raw.get("id"):
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

    seen: set[str] = set()
    unique: list[Track] = []
    for t in tracks:
        if t.spotify_id not in seen:
            seen.add(t.spotify_id)
            unique.append(t)

    if not unique and total_in_playlist:
        raise ValueError(
            f"Playlist heeft {total_in_playlist} nummers maar geen konden worden geladen. "
            "Mogelijk zijn alle nummers lokale bestanden of niet beschikbaar in jouw markt."
        )

    return playlist_name, unique
