"""
Eenmalig uitvoeren om een Spotify refresh token te verkrijgen.

Het gegenereerde refresh token hoeft maar één keer opgeslagen te worden in
.streamlit/secrets.toml (en in Streamlit Cloud secrets). De app gebruikt
daarna dit token automatisch, zonder dat gebruikers hoeven in te loggen.

Gebruik:
    python scripts/spotify_auth.py
"""
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # pip install tomli op Python < 3.11

secrets_path = Path(".streamlit/secrets.toml")
if not secrets_path.exists():
    secrets_path = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"

with open(secrets_path, "rb") as f:
    secrets = tomllib.load(f)

client_id = secrets["SPOTIFY_CLIENT_ID"]
client_secret = secrets["SPOTIFY_CLIENT_SECRET"]
redirect_uri = secrets.get("SPOTIFY_REDIRECT_URI", "http://localhost:8501")

import base64
import requests

SCOPE = "playlist-read-private playlist-read-collaborative"

auth_url = (
    "https://accounts.spotify.com/authorize"
    f"?client_id={client_id}"
    f"&response_type=code"
    f"&redirect_uri={redirect_uri}"
    f"&scope={SCOPE.replace(' ', '%20')}"
)

print("Stap 1: Open deze URL in je browser:\n")
print(f"  {auth_url}\n")
print("Stap 2: Log in bij Spotify en klik op Akkoord.")
print("Stap 3: Kopieer de volledige callback-URL uit je adresbalk en plak hem hieronder:\n")

callback_url = input("Callback URL: ").strip()
params = parse_qs(urlparse(callback_url).query)

if "code" not in params:
    print("❌ Geen 'code' gevonden in de URL.")
    sys.exit(1)

code = params["code"][0]
creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
resp = requests.post(
    "https://accounts.spotify.com/api/token",
    headers={
        "Authorization": f"Basic {creds}",
        "Content-Type": "application/x-www-form-urlencoded",
    },
    data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    },
)
resp.raise_for_status()
token_info = resp.json()

refresh_token = token_info.get("refresh_token", "")
if not refresh_token:
    print("❌ Geen refresh token ontvangen.")
    sys.exit(1)

print("\n✅ Gelukt! Voeg dit toe aan .streamlit/secrets.toml en Streamlit Cloud secrets:\n")
print(f'SPOTIFY_REFRESH_TOKEN = "{refresh_token}"\n')
