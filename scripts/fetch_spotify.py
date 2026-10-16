"""Write data/now_playing.json from Spotify: the current track, else the last one played.

Needs SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN. The album cover is
dithered to 1-bit here (Pillow) and embedded as base64 so render.py stays stdlib-only.
"""
import base64
import datetime as dt
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "now_playing.json"
COVER = 64  # dither resolution; rendered at 2x

BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def env(name: str) -> str:
    return os.environ.get(name) or sys.exit(f"{name} is not set")


def access_token() -> str:
    auth = base64.b64encode(f"{env('SPOTIFY_CLIENT_ID')}:{env('SPOTIFY_CLIENT_SECRET')}".encode()).decode()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": env("SPOTIFY_REFRESH_TOKEN")}).encode(),
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["access_token"]


def get(path: str, token: str) -> dict | None:
    req = urllib.request.Request(f"https://api.spotify.com/v1{path}", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r) if r.status == 200 else None


def dither_cover(url: str) -> str | None:
    """1-bit Bayer-dithered PNG of the cover, base64. Skipped if Pillow is missing."""
    try:
        from PIL import Image, ImageEnhance, ImageOps
    except ImportError:
        return None
    with urllib.request.urlopen(url, timeout=30) as r:
        im = Image.open(io.BytesIO(r.read()))
    g = ImageOps.grayscale(im).resize((COVER, COVER), Image.LANCZOS)
    g = ImageEnhance.Contrast(g).enhance(1.4)
    px = g.load()
    out = Image.new("1", (COVER, COVER))
    op = out.load()
    for y in range(COVER):
        for x in range(COVER):
            op[x, y] = 1 if px[x, y] / 255 > (BAYER4[y % 4][x % 4] + 0.5) / 16 else 0
    out = out.resize((COVER * 2, COVER * 2), Image.NEAREST)
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def main() -> None:
    token = access_token()
    now = dt.datetime.now(dt.timezone.utc)
    track, playing, played_at = None, False, None
    cur = get("/me/player/currently-playing", token)
    if cur and cur.get("item") and cur["item"].get("type") == "track":
        track, playing = cur["item"], bool(cur.get("is_playing"))
    if track is None:
        recent = get("/me/player/recently-played?limit=1", token)
        if recent and recent.get("items"):
            track, played_at = recent["items"][0]["track"], recent["items"][0]["played_at"]

    data = {"fetched_at": now.isoformat(timespec="seconds"), "track": None}
    if track:
        images = track.get("album", {}).get("images") or []
        cover = images[-1]["url"] if images else None  # smallest
        data["track"] = {
            "title": track["name"],
            "artist": ", ".join(a["name"] for a in track["artists"]),
            "album": track["album"]["name"],
            "url": track["external_urls"].get("spotify"),
            "is_playing": playing,
            "played_at": played_at,
            "cover_1bit": dither_cover(cover) if cover else None,
        }
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    t = data["track"]
    print(f"{OUT}: " + (f"{'▶' if t['is_playing'] else '■'} {t['artist']} — {t['title']}" if t else "nothing played"))


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        sys.exit(f"Spotify {e.code}: {e.read()[:200]!r}")
