"""Assemble assets/hero.svg: 1-bit dithered artwork + CSS/SMIL motion. No JS, fonts embedded (GitHub-safe).

One-off build (not run by the Action). Needs: pip install pillow numpy fonttools
    python scripts/art/dither.py art/wizard-source.png art/wizard-1bit.png \
        --crop 60,0,1376,740 --paper-to-black --width 450 --scale 2 --contrast 1.6 --gamma 1.3
    python scripts/art/build_hero.py

Geometry below is in the 900x502 artwork space; re-measure it if the artwork changes.
"""
import base64
import sys
from pathlib import Path

import numpy as np
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
FONTS = ROOT / "assets/fonts"
PNG = ROOT / "art/wizard-1bit.png"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "assets/hero.svg"

W, AH, BAND = 900, 502, 96   # width, artwork height, status band height
H = AH + BAND

INK = "#cfc3ff"      # lavender "white"
BG = "#050308"
ACID = "#b8ff4a"     # terminal / screen
VIOLET = "#9d5cff"   # crystal / magic
PINK = "#ff5fd2"

ART = {
    "screen": (106, 200, 282, 408),      # CRT glass, x0 y0 x1 y1
    "ball": (578, 397, 62),              # crystal ball cx cy r
    "sparks": (180, 20, 155, 160),      # spell hand, x y w h
    "alfred": (650, 0, 250, AH),         # the familiar, flickers on ./summon
    "glitch_y": 236,
}


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def font_face(name: str, file: str) -> str:
    return f"@font-face{{font-family:'{name}';src:url(data:font/woff2;base64,{b64(FONTS / file)}) format('woff2');}}"


def mono_advance(file: str, size: float) -> float:
    f = TTFont(FONTS / file)
    return f["hmtx"]["a"][0] * size / f["head"].unitsPerEm


sx0, sy0, sx1, sy1 = ART["screen"]
bcx, bcy, br = ART["ball"]
kx, ky, kw, kh = ART["sparks"]
ax, ay, aw, ah = ART["alfred"]

# --- status band: terminal on the right, typed line by line -----------------
TERM_SIZE = 17
adv = mono_advance("VT323-Regular.woff2", TERM_SIZE)
lines = [
    ("mau@dungeon ~ % whoami", ACID, 0.6, 1.0),
    ("code wizard · ships with AI agents", INK, 1.8, 1.3),
    ("mau@dungeon ~ % ./summon alfred", ACID, 3.7, 1.4),
    ("alfred: your tea, sir.", PINK, 5.9, 1.0),
]
line_h = 21
term_w = max(len(t) for t, *_ in lines) * adv
term_x = W - 26 - term_w
term_y0 = AH + 24
term_svg, term_defs = [], []
for i, (txt, color, start, dur) in enumerate(lines):
    n = len(txt)
    y = term_y0 + i * line_h
    # SMIL typewriter: clip rect widens one glyph at a time (discrete keyframes)
    values = ";".join(f"{k * adv:.1f}" for k in range(n + 1))
    term_defs.append(
        f'<clipPath id="tc{i}"><rect x="{term_x:.1f}" y="{y - TERM_SIZE}" width="0" height="{line_h}">'
        f'<animate attributeName="width" values="{values}" calcMode="discrete" begin="{start}s" dur="{dur}s" fill="freeze"/></rect></clipPath>'
    )
    term_svg.append(f'<text x="{term_x:.1f}" y="{y - 3}" class="term" fill="{color}" clip-path="url(#tc{i})">{txt}</text>')
SUBTITLE = "Forward Deployed Software Engineer @ Palo Alto Collaboration Co. · Querétaro, MX"
sub_end = 26 + len(SUBTITLE) * mono_advance("VT323-Regular.woff2", 16)
assert sub_end < term_x - 12, f"subtitle ({sub_end:.0f}px) runs into the terminal ({term_x:.0f}px)"
cursor_y = term_y0 + (len(lines) - 1) * line_h
cursor_x = term_x + len(lines[-1][0]) * adv + 2
cursor_show = lines[-1][2] + lines[-1][3]
summon_at = lines[2][2] + lines[2][3] + 0.3

# --- particles rising from the crystal ball ---------------------------------
rng = np.random.default_rng(7)
particles = []
for i in range(14):
    px = bcx + rng.uniform(-br * 0.8, br * 0.8)
    py = bcy - rng.uniform(0, br * 0.6)
    d = rng.uniform(2.4, 4.8)
    delay = rng.uniform(0, 4)
    r = rng.choice([1.5, 2, 2.5])
    col = [VIOLET, PINK, INK][i % 3]
    particles.append(
        f'<circle cx="{px:.0f}" cy="{py:.0f}" r="{r}" fill="{col}" class="p" style="animation-duration:{d:.1f}s;animation-delay:{delay:.1f}s"/>'
    )

css = f"""
{font_face('Jacquard', 'Jacquard12-Regular.woff2')}
{font_face('VT323', 'VT323-Regular.woff2')}
.name{{font-family:'Jacquard','Courier New',monospace;font-size:44px;fill:{INK};}}
.sub{{font-family:'VT323','Courier New',monospace;font-size:16px;fill:{ACID};letter-spacing:.5px}}
.term{{font-family:'VT323','Courier New',monospace;font-size:{TERM_SIZE}px;white-space:pre}}
.cursor{{opacity:0;animation:blink 1s steps(2,start) infinite;animation-delay:{cursor_show:.1f}s}}
@keyframes blink{{to{{opacity:1}}}}
.crt{{transform-origin:50% 50%;animation:poweron 1.1s cubic-bezier(.2,.9,.3,1) both}}
@keyframes poweron{{0%{{transform:scaleY(.004) scaleX(1.2);opacity:1}}35%{{transform:scaleY(.004) scaleX(1.2)}}60%{{transform:scaleY(1) scaleX(1.02);opacity:1}}100%{{transform:none}}}}
.flash{{animation:flash 1.1s ease-out both}}
@keyframes flash{{0%,35%{{opacity:.9}}70%{{opacity:.15}}100%{{opacity:0}}}}
.screen{{animation:screen 3.2s ease-in-out infinite}}
@keyframes screen{{0%,100%{{opacity:.78}}50%{{opacity:1}}}}
.scan{{animation:scan 4s linear infinite}}
@keyframes scan{{from{{transform:translateY(-60px)}}to{{transform:translateY({sy1 - sy0 + 60}px)}}}}
.ballglow{{transform-origin:{bcx}px {bcy}px;animation:ball 2.6s ease-in-out infinite}}
@keyframes ball{{0%,100%{{transform:scale(1);opacity:.55}}50%{{transform:scale(1.18);opacity:.95}}}}
.p{{opacity:0;animation-name:rise;animation-timing-function:ease-out;animation-iteration-count:infinite}}
@keyframes rise{{0%{{opacity:0;transform:translateY(0)}}15%{{opacity:1}}100%{{opacity:0;transform:translateY(-110px)}}}}
.spark{{animation:spark 1.7s steps(1,end) infinite}}
@keyframes spark{{0%{{opacity:.2}}8%{{opacity:1}}14%{{opacity:.3}}22%{{opacity:.9}}30%{{opacity:.15}}55%{{opacity:.6}}62%{{opacity:.1}}80%{{opacity:.8}}}}
.lines{{animation:drift 9s linear infinite}}
@keyframes drift{{from{{transform:translateY(0)}}to{{transform:translateY(4px)}}}}
.glitch{{opacity:0;animation:glitch 9s steps(1,end) infinite}}
@keyframes glitch{{0%,100%{{opacity:0;transform:none}}41%{{opacity:1;transform:translateX(7px)}}42.2%{{opacity:1;transform:translateX(-5px)}}43.4%{{opacity:0;transform:none}}77%{{opacity:1;transform:translateX(-6px)}}78%{{opacity:0;transform:none}}}}
.summon{{opacity:0;animation:summon .7s steps(1,end) {summon_at:.1f}s forwards}}
@keyframes summon{{0%{{opacity:0}}15%{{opacity:.85}}30%{{opacity:0}}45%{{opacity:.85}}60%{{opacity:0}}70%{{opacity:.6}}100%{{opacity:0}}}}
.summonglow{{opacity:0;animation:summonglow 1.2s ease-out {summon_at:.1f}s forwards}}
@keyframes summonglow{{0%{{opacity:0}}30%{{opacity:.9}}100%{{opacity:0}}}}
.vignette{{opacity:.55}}
"""

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Mauricio Chavez — code wizard, with Alfred">
<title>Mauricio Chavez — code wizard, with Alfred</title>
<style>{css}</style>
<defs>
  <image id="art" href="data:image/png;base64,{b64(PNG)}" width="{W}" height="{AH}" preserveAspectRatio="xMidYMid slice"/>
  <mask id="ink"><use href="#art"/></mask>
  <clipPath id="artclip"><rect x="0" y="0" width="{W}" height="{AH}"/></clipPath>
  <clipPath id="screenclip"><rect x="{sx0}" y="{sy0}" width="{sx1 - sx0}" height="{sy1 - sy0}" rx="10"/></clipPath>
  <clipPath id="ballclip"><circle cx="{bcx}" cy="{bcy}" r="{br}"/></clipPath>
  <clipPath id="sparkclip"><rect x="{kx}" y="{ky}" width="{kw}" height="{kh}"/></clipPath>
  <clipPath id="alfredclip"><rect x="{ax}" y="{ay}" width="{aw}" height="{ah}"/></clipPath>
  <clipPath id="glitchclip"><rect x="0" y="{ART['glitch_y']}" width="{W}" height="22"/></clipPath>
  <radialGradient id="screenglow" cx="50%" cy="50%" r="65%"><stop offset="0" stop-color="{ACID}"/><stop offset="1" stop-color="{ACID}" stop-opacity=".55"/></radialGradient>
  <radialGradient id="ballfill" cx="40%" cy="35%" r="70%"><stop offset="0" stop-color="#fff"/><stop offset=".35" stop-color="{PINK}"/><stop offset="1" stop-color="{VIOLET}"/></radialGradient>
  <radialGradient id="halo"><stop offset="0" stop-color="{VIOLET}" stop-opacity=".9"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>
  <radialGradient id="screenhalo"><stop offset="0" stop-color="{ACID}" stop-opacity=".55"/><stop offset="1" stop-color="{ACID}" stop-opacity="0"/></radialGradient>
  <radialGradient id="vig" cx="50%" cy="45%" r="75%"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="1"/></radialGradient>
  <pattern id="scanlines" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="2" fill="#000" opacity=".28"/></pattern>
  <pattern id="dots" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="1" height="1" fill="{INK}"/><rect x="2" y="2" width="1" height="1" fill="{INK}"/></pattern>
  {''.join(term_defs)}
  <filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="14"/></filter>
</defs>

<rect width="{W}" height="{H}" fill="{BG}"/>
<g class="crt">
  <g clip-path="url(#artclip)">
    <!-- soft halos under the art -->
    <circle cx="{bcx}" cy="{bcy}" r="{br * 1.9:.0f}" fill="url(#halo)" class="ballglow" filter="url(#blur)"/>
    <ellipse cx="{(sx0 + sx1) / 2:.0f}" cy="{(sy0 + sy1) / 2:.0f}" rx="{(sx1 - sx0) * 0.9:.0f}" ry="{(sy1 - sy0) * 0.75:.0f}" fill="url(#screenhalo)" class="screen" filter="url(#blur)"/>
    <rect x="{ax}" y="{ay}" width="{aw}" height="{ah}" fill="{VIOLET}" class="summonglow" filter="url(#blur)"/>

    <!-- the 1-bit artwork: ink pixels tinted lavender via mask -->
    <g mask="url(#ink)">
      <rect width="{W}" height="{AH}" fill="{INK}"/>
      <!-- CRT face: acid green + traveling scan band -->
      <g clip-path="url(#screenclip)">
        <rect x="{sx0}" y="{sy0}" width="{sx1 - sx0}" height="{sy1 - sy0}" fill="url(#screenglow)" class="screen"/>
        <rect x="{sx0}" y="{sy0}" width="{sx1 - sx0}" height="34" fill="#fff" opacity=".35" class="scan"/>
      </g>
      <!-- crystal ball: violet/pink -->
      <g clip-path="url(#ballclip)"><circle cx="{bcx}" cy="{bcy}" r="{br}" fill="url(#ballfill)"/></g>
      <!-- spell sparks: flicker -->
      <g clip-path="url(#sparkclip)"><rect x="{kx}" y="{ky}" width="{kw}" height="{kh}" fill="{ACID}" class="spark"/></g>
    </g>

    <!-- ./summon: Alfred flickers violet -->
    <g clip-path="url(#alfredclip)" mask="url(#ink)"><rect width="{W}" height="{AH}" fill="{VIOLET}" class="summon"/></g>

    <!-- glitch slice: a displaced copy of one horizontal band -->
    <g clip-path="url(#glitchclip)" class="glitch" mask="url(#ink)"><rect width="{W}" height="{AH}" fill="{PINK}" opacity=".9"/></g>

    {''.join(particles)}

    <!-- scanlines + vignette -->
    <g class="lines"><rect x="0" y="-8" width="{W}" height="{AH + 16}" fill="url(#scanlines)"/></g>
    <rect width="{W}" height="{AH}" fill="url(#vig)" class="vignette"/>
  </g>

  <!-- status band -->
  <rect x="0" y="{AH}" width="{W}" height="{BAND}" fill="{BG}"/>
  <rect x="2" y="{AH + 2}" width="{W - 4}" height="{BAND - 4}" fill="none" stroke="{INK}" stroke-width="2"/>
  <rect x="7" y="{AH + 7}" width="{W - 14}" height="{BAND - 14}" fill="none" stroke="{INK}" stroke-width="1" opacity=".5"/>
  <rect x="4" y="{AH + 4}" width="{W - 8}" height="3" fill="url(#dots)"/>
  <text x="24" y="{AH + 50}" class="name">Mauricio Chavez</text>
  <text x="26" y="{AH + 76}" class="sub">{SUBTITLE}</text>
  {''.join(term_svg)}
  <rect x="{cursor_x:.0f}" y="{cursor_y - TERM_SIZE + 3}" width="{adv:.0f}" height="{TERM_SIZE}" fill="{PINK}" class="cursor"/>
</g>
<rect width="{W}" height="{H}" fill="#fff" class="flash" pointer-events="none"/>
</svg>
"""

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(svg)
print(f"{OUT}: {len(svg.encode()) / 1024:.0f} KB", file=sys.stderr)
