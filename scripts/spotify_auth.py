"""One-time Spotify authorization for the now-spinning widget.

Run this in your own terminal (not through an agent), so the secret never lands in a transcript:

    python scripts/spotify_auth.py url <client_id>
        prints the URL to open; approve, then copy the http://127.0.0.1:8888/callback?code=... URL

    python scripts/spotify_auth.py token <client_id> '<callback_url>'
        asks for the client secret, exchanges the code and stores SPOTIFY_REFRESH_TOKEN
        as a repository secret with `gh secret set`.
"""
import base64
import getpass
import json
import subprocess
import sys
import urllib.parse
import urllib.request

REDIRECT = "http://127.0.0.1:8888/callback"
SCOPES = "user-read-currently-playing user-read-recently-played"
REPO = "ultr4nerd/ultr4nerd"


def main() -> None:
    if len(sys.argv) < 3 or sys.argv[1] not in ("url", "token"):
        sys.exit(__doc__)
    mode, client_id = sys.argv[1], sys.argv[2]
    if mode == "url":
        q = urllib.parse.urlencode({"client_id": client_id, "response_type": "code", "redirect_uri": REDIRECT, "scope": SCOPES})
        print(f"https://accounts.spotify.com/authorize?{q}")
        return

    callback = sys.argv[3] if len(sys.argv) > 3 else input("callback URL: ")
    code = urllib.parse.parse_qs(urllib.parse.urlparse(callback).query).get("code", [None])[0]
    if not code:
        sys.exit("no ?code= in that URL")
    secret = getpass.getpass("client secret (hidden): ")
    auth = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=urllib.parse.urlencode({"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT}).encode(),
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        tok = json.load(r)
    refresh = tok["refresh_token"]
    subprocess.run(["gh", "secret", "set", "SPOTIFY_REFRESH_TOKEN", "-R", REPO], input=refresh.encode(), check=True)
    subprocess.run(["gh", "secret", "set", "SPOTIFY_CLIENT_ID", "-R", REPO], input=client_id.encode(), check=True)
    print("stored SPOTIFY_REFRESH_TOKEN and SPOTIFY_CLIENT_ID. Now set the secret too:\n"
          f"  gh secret set SPOTIFY_CLIENT_SECRET -R {REPO}")


if __name__ == "__main__":
    main()
