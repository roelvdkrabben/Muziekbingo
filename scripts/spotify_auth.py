"""
Eenmalig uitvoeren om Spotify-toegang te autoriseren.
Daarna wordt de token automatisch ge-refresht door de app.

Gebruik:
    python scripts/spotify_auth.py
"""
import sys
import os
from pathlib import Path

# Zorg dat de project-root in sys.path staat
sys.path.insert(0, str(Path(__file__).parent.parent))

# Laad secrets uit .streamlit/secrets.toml
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # pip install tomli op Python < 3.11

secrets_path = Path(".streamlit/secrets.toml")
if not secrets_path.exists():
    secrets_path = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"

with open(secrets_path, "rb") as f:
    secrets = tomllib.load(f)

os.environ["SPOTIFY_CLIENT_ID"] = secrets["SPOTIFY_CLIENT_ID"]
os.environ["SPOTIFY_CLIENT_SECRET"] = secrets["SPOTIFY_CLIENT_SECRET"]

# ────────────────────────────────────────────────────────────────────────────────
import http.server
import threading
import webbrowser
from urllib.parse import urlparse, parse_qs

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from core.spotify_client import CACHE_PATH, SCOPE, REDIRECT_URI

Path("data").mkdir(exist_ok=True)

auth = SpotifyOAuth(
    client_id=os.environ["SPOTIFY_CLIENT_ID"],
    client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_path=str(CACHE_PATH),
    open_browser=False,
)

# Check of we al een geldige token hebben
cached = auth.get_cached_token()
if cached and not auth.is_token_expired(cached):
    print("✅ Al geauthenticeerd — token is geldig.")
    sp = spotipy.Spotify(auth_manager=auth)
    user = sp.current_user()
    print(f"   Ingelogd als: {user['display_name']} ({user['id']})")
    sys.exit(0)

auth_url = auth.get_authorize_url()
print("Stap 1: Open deze URL in je browser:\n")
print(f"  {auth_url}\n")
print("Stap 2: Autoriseer de app.")
print("Stap 3: Je wordt doorgestuurd naar een URL die begint met http://localhost:8888/callback")
print("        Kopieer die volledige URL en plak hem hieronder:\n")

callback_url = input("Callback URL: ").strip()

parsed = urlparse(callback_url)
params = parse_qs(parsed.query)

if "code" not in params:
    print("❌ Geen 'code' gevonden in de URL. Probeer opnieuw.")
    sys.exit(1)

code = params["code"][0]
token_info = auth.get_access_token(code, as_dict=True, check_cache=False)

if token_info:
    print(f"\n✅ Geauthenticeerd! Token opgeslagen in: {CACHE_PATH}")
    sp = spotipy.Spotify(auth_manager=auth)
    user = sp.current_user()
    print(f"   Ingelogd als: {user['display_name']} ({user['id']})")
    print("\nJe kunt de Streamlit app nu normaal gebruiken.")
else:
    print("❌ Token ophalen mislukt.")
    sys.exit(1)
