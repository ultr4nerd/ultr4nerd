"""Render the animated profile widgets from data/stats.json into assets/.

Stdlib only. Every SVG is self-contained (fonts embedded, no JS) so GitHub's
image proxy renders it with the CSS/SMIL animations intact.
"""
import base64
import datetime as dt
import json
import random
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
STATS = json.loads((ROOT / "data" / "stats.json").read_text())

BG, INK, DIM = "#050308", "#cfc3ff", "#5a4f86"
ACID, VIOLET, PINK = "#b8ff4a", "#9d5cff", "#ff5fd2"

# VT323 is monospaced: advance = 0.4em. Lets us lay out text without measuring.
MONO_ADV = 0.4


def font_css() -> str:
    faces = []
    for family, file in (("Jacquard", "Jacquard12-Regular.woff2"), ("VT323", "VT323-Regular.woff2"), ("Silkscreen", "Silkscreen-Regular.woff2")):
        b = base64.b64encode((ASSETS / "fonts" / file).read_bytes()).decode()
        faces.append(f"@font-face{{font-family:'{family}';src:url(data:font/woff2;base64,{b}) format('woff2')}}")
    return "".join(faces) + (
        f".h{{font-family:'Jacquard','Courier New',monospace;fill:{INK}}}"
        f".m{{font-family:'VT323','Courier New',monospace;fill:{INK};white-space:pre}}"
        f".s{{font-family:'Silkscreen','Courier New',monospace;fill:{INK}}}"
        f".dim{{fill:{DIM}}}.acid{{fill:{ACID}}}.pink{{fill:{PINK}}}.violet{{fill:{VIOLET}}}"
    )


COMMON_DEFS = f"""
<pattern id="dots" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="1" height="1" fill="{INK}"/><rect x="2" y="2" width="1" height="1" fill="{INK}"/></pattern>
<pattern id="gaps" width="10" height="4" patternUnits="userSpaceOnUse"><rect x="8" width="2" height="4" fill="{BG}"/></pattern>
<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="2" fill="#000" opacity=".22"/></pattern>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>
"""


def frame(w: int, h: int) -> str:
    """double pixel border with a dotted band and corner ticks, like an old CRPG window"""
    return (
        f'<rect x="2" y="2" width="{w - 4}" height="{h - 4}" fill="none" stroke="{INK}" stroke-width="2"/>'
        f'<rect x="7" y="7" width="{w - 14}" height="{h - 14}" fill="none" stroke="{INK}" stroke-width="1" opacity=".5"/>'
        f'<rect x="4" y="4" width="{w - 8}" height="3" fill="url(#dots)"/><rect x="4" y="{h - 7}" width="{w - 8}" height="3" fill="url(#dots)"/>'
        + "".join(
            f'<rect x="{x}" y="{y}" width="6" height="6" fill="{ACID}"/>'
            for x, y in ((0, 0), (w - 6, 0), (0, h - 6), (w - 6, h - 6))
        )
    )


def reveal(delay: float, dur: float = 0.5) -> str:
    return f'style="opacity:0;animation:fade {dur}s steps(4,end) {delay:.2f}s forwards"'


def grow(width: float, delay: float, dur: float = 1.1) -> str:
    """SMIL width animation (works inside <img>, which CSS geometry doesn't always)"""
    return (f'<animate attributeName="width" from="0" to="{width:.1f}" begin="{delay:.2f}s" dur="{dur}s" '
            'fill="freeze" calcMode="spline" keySplines=".2 .8 .2 1"/>')


def bar(x: float, y: float, w: float, h: float, frac: float, color: str, delay: float) -> str:
    frac = max(0.0, min(1.0, frac))
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#dots)" opacity=".5"/>'
        f'<rect x="{x}" y="{y}" width="0" height="{h}" fill="{color}">{grow(w * frac, delay)}</rect>'
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#gaps)"/>'
        f'<rect x="{x - 1}" y="{y - 1}" width="{w + 2}" height="{h + 2}" fill="none" stroke="{INK}" opacity=".35"/>'
    )


def svg(w: int, h: int, body: str, css: str = "", label: str = "") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(label)}">'
        f"<title>{escape(label)}</title><style>{font_css()}@keyframes fade{{to{{opacity:1}}}}{css}</style>"
        f"<defs>{COMMON_DEFS}</defs><rect width=\"{w}\" height=\"{h}\" fill=\"{BG}\"/>{body}"
        f'<rect width="{w}" height="{h}" fill="url(#scan)"/></svg>'
    )


def n(v: int) -> str:
    return f"{v:,}"


# --------------------------------------------------------------------------- character sheet
def character_sheet() -> str:
    W, H = 900, 400
    t, st = STATS["totals"], STATS["streak"]
    created = dt.datetime.fromisoformat(STATS["user"]["created_at"].replace("Z", "+00:00")).date()
    today = dt.datetime.fromisoformat(STATS["generated_at"]).date()
    level = today.year - created.year - ((today.month, today.day) < (created.month, created.day))
    last_anniv = created.replace(year=created.year + level)
    next_anniv = created.replace(year=created.year + level + 1)
    xp = (today - last_anniv).days / (next_anniv - last_anniv).days
    portrait = base64.b64encode((ROOT / "art" / "portrait-1bit.png").read_bytes()).decode()

    d = 0.15  # reveal cadence
    body = [frame(W, H)]
    # --- portrait + identity
    body.append(f'<g {reveal(0.1)}><rect x="26" y="26" width="204" height="204" fill="{INK}"/>'
                f'<mask id="pm"><image href="data:image/png;base64,{portrait}" x="28" y="28" width="200" height="200"/></mask>'
                f'<rect x="28" y="28" width="200" height="200" fill="{BG}"/><rect x="28" y="28" width="200" height="200" fill="{INK}" mask="url(#pm)"/>'
                f'<rect x="28" y="28" width="200" height="200" fill="url(#scan)"/></g>')
    body.append(f'<text x="28" y="282" class="h" font-size="44" {reveal(0.4)}>Mau</text>')
    body.append(f'<text x="28" y="308" class="m acid" font-size="20" {reveal(0.55)}>CODE WIZARD · LV {level}</text>')
    body.append(f'<text x="28" y="330" class="m dim" font-size="17" {reveal(0.7)}>{escape(STATS["user"]["name"])}</text>')
    body.append(f'<text x="28" y="350" class="m dim" font-size="17" {reveal(0.8)}>@{STATS["user"]["login"]} · since {created.year}</text>')
    body.append(f'<text x="28" y="370" class="m dim" font-size="17" {reveal(0.9)}>Querétaro, MX</text>')

    # --- vitals (center)
    x0, bw = 268, 300
    vitals = [
        ("XP", f"LV {level} · next level in {(next_anniv - today).days}d", xp, ACID),
        ("HP", f"streak {st['current']}d · best {st['longest']}d", st["current"] / max(st["longest"], 1), PINK),
        ("MP", f"this week {STATS['this_week']} · best week {STATS['best_week']}", STATS["this_week"] / max(STATS["best_week"], 1), VIOLET),
    ]
    body.append(f'<text x="{x0}" y="46" class="h" font-size="26" {reveal(0.3)}>Vitals</text>')
    y = 70
    for i, (k, label, frac, color) in enumerate(vitals):
        dl = 0.5 + i * 0.25
        body.append(f'<g {reveal(dl)}><text x="{x0}" y="{y + 12}" class="s" font-size="11" fill="{color}">{k}</text>'
                    f'<text x="{x0 + 38}" y="{y + 12}" class="m" font-size="17">{escape(label)}</text></g>')
        body.append(bar(x0, y + 20, bw, 12, frac, color, dl + 0.1))
        y += 48

    # --- ledger
    rows = [
        ("CONTRIBUTIONS", f"{n(t['contributions_all_time'])} all-time"),
        ("LAST 12 MONTHS", f"{n(t['contributions_12mo'])} · {n(t['private_12mo'])} private"),
        ("STARS", f"{n(t['stars'])}"),
        ("REPOS", f"{n(t['repos'])} · {n(t['repos_public'])} public"),
        ("FOLLOWERS", f"{n(STATS['user']['followers'])}"),
    ]
    y = 232
    body.append(f'<text x="{x0}" y="{y}" class="h" font-size="26" {reveal(1.3)}>Ledger</text>')
    y += 26
    for i, (k, v) in enumerate(rows):
        body.append(f'<g {reveal(1.45 + i * d)}><text x="{x0}" y="{y}" class="m dim" font-size="17">{k}</text>'
                    f'<text x="{x0 + 150}" y="{y}" class="m" font-size="17">{escape(v)}</text></g>')
        y += 24

    # --- equipment (right)
    x1, ew = 608, 200
    body.append(f'<text x="{x1}" y="46" class="h" font-size="26" {reveal(0.3)}>Equipment</text>')
    y = 66
    top = STATS["languages"][0]["pct"] if STATS["languages"] else 1
    for i, lang in enumerate(STATS["languages"][:5]):
        dl = 0.6 + i * 0.2
        body.append(f'<g {reveal(dl)}><text x="{x1}" y="{y + 12}" class="m" font-size="17">{escape(lang["name"])}</text>'
                    f'<text x="{x1 + ew + 62}" y="{y + 12}" class="m acid" font-size="17" text-anchor="end">{lang["pct"]:.0f}%</text></g>')
        body.append(bar(x1, y + 18, ew + 62, 8, lang["pct"] / top, INK, dl + 0.1))
        y += 36
    y += 10
    body.append(f'<text x="{x1}" y="{y + 10}" class="h" font-size="26" {reveal(1.7)}>Spellbook</text>')
    spells = [("Claude Code", "weapon"), ("Pi", "sidearm"), ("Pana · Alfred", "familiar"), ("Vinyl + CDJs", "off-hand")]
    y += 44
    for i, (s, slot) in enumerate(spells):
        body.append(f'<g {reveal(1.85 + i * d)}><text x="{x1}" y="{y}" class="m" font-size="17">{s}</text>'
                    f'<text x="{x1 + ew + 62}" y="{y}" class="m dim" font-size="17" text-anchor="end">{slot}</text></g>')
        y += 22

    body.append(f'<text x="{W - 26}" y="{H - 14}" class="m dim" font-size="14" text-anchor="end" {reveal(2.5)}>'
                f'synced {today.isoformat()} · private contributions included</text>')
    body.append(f'<rect x="{W - 20}" y="{H - 23}" width="4" height="4" fill="{ACID}" style="animation:fade .9s steps(2,start) infinite"/>')
    return svg(W, H, "".join(body), label="Character sheet")


# --------------------------------------------------------------------------- contribution equalizer
def equalizer() -> str:
    W, H = 900, 250
    weeks = STATS["weeks"]
    totals = [sum(c for _, c in w) for w in weeks]
    peak = max(totals) or 1
    left, right, top, base = 24, W - 24, 58, H - 40
    slot = (right - left) / len(weeks)
    bw = slot * 0.72
    maxh = base - top
    rng = random.Random(len(weeks))
    bars, labels, seen = [], [], set()
    for i, (w, total) in enumerate(zip(weeks, totals)):
        h = max(2.0, maxh * total / peak)
        x = left + i * slot + (slot - bw) / 2
        dur = rng.uniform(0.7, 1.5)
        amp = rng.uniform(0.8, 0.92)
        bars.append(
            f'<g style="transform-origin:{x + bw / 2:.1f}px {base}px;animation:bounce {dur:.2f}s ease-in-out {rng.uniform(0, 1):.2f}s infinite alternate;--a:{amp:.2f}">'
            f'<rect x="{x:.1f}" y="{base - h:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="url(#meter)">'
            f'<animate attributeName="height" from="0" to="{h:.1f}" begin="{0.2 + i * 0.02:.2f}s" dur=".6s" fill="freeze" calcMode="spline" keySplines=".2 .8 .2 1"/>'
            f'<animate attributeName="y" from="{base}" to="{base - h:.1f}" begin="{0.2 + i * 0.02:.2f}s" dur=".6s" fill="freeze" calcMode="spline" keySplines=".2 .8 .2 1"/>'
            f"</rect></g>"
        )
        month = dt.date.fromisoformat(w[0][0]).strftime("%b")
        if w[0][0][:7] not in seen and i > 0:
            seen.add(w[0][0][:7])
            labels.append(f'<text x="{x:.1f}" y="{base + 20}" class="m dim" font-size="14">{month.upper()}</text>')
    now_x = left + (len(weeks) - 1) * slot + slot / 2
    body = [
        frame(W, H),
        f'<text x="24" y="38" class="h" font-size="26" {reveal(0.1)}>Now playing</text>',
        f'<text x="196" y="36" class="m acid" font-size="19" {reveal(0.3)}>ultr4nerd — 52-week set</text>',
        f'<text x="{W - 24}" y="36" class="m" font-size="19" text-anchor="end" {reveal(0.5)}>'
        f'{n(STATS["totals"]["contributions_12mo"])} contributions · peak {peak}/wk</text>',
        f'<line x1="{left}" y1="{base + 1}" x2="{right}" y2="{base + 1}" stroke="{INK}" opacity=".4"/>',
        # LED rows: horizontal gaps across the whole meter
        "".join(bars),
        f'<rect x="{left}" y="{top}" width="{right - left}" height="{maxh}" fill="url(#rows)"/>',
        "".join(labels),
        # playhead sweeping the set
        f'<g style="animation:sweep 12s linear 1s infinite"><rect x="{left - 1}" y="{top - 6}" width="2" height="{maxh + 12}" fill="{ACID}"/>'
        f'<rect x="{left - 6}" y="{top - 6}" width="12" height="{maxh + 12}" fill="{ACID}" opacity=".35" filter="url(#glow)"/></g>',
        # "now" marker
        f'<text x="{now_x:.0f}" y="{top - 10}" class="s acid" font-size="9" text-anchor="middle" style="animation:fade .8s steps(2,start) infinite">NOW</text>',
    ]
    css = (
        "@keyframes bounce{from{transform:scaleY(1)}to{transform:scaleY(var(--a))}}"
        f"@keyframes sweep{{from{{transform:translateX(0)}}to{{transform:translateX({right - left}px)}}}}"
    )
    defs = (
        f'<linearGradient id="meter" x1="0" y1="{base}" x2="0" y2="{top}" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="{VIOLET}"/><stop offset=".55" stop-color="{ACID}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>'
        f'<pattern id="rows" width="4" height="6" patternUnits="userSpaceOnUse"><rect y="4" width="4" height="2" fill="{BG}"/></pattern>'
    )
    return svg(W, H, f"<defs>{defs}</defs>" + "".join(body), css, label="Contributions, last 52 weeks")


# --------------------------------------------------------------------------- cartridges
def wrap(text: str, size: int, width: float, max_lines: int) -> list[str]:
    per = int(width / (size * MONO_ADV))
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) > per:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}" if cur else w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: per - 1].rstrip() + "…"
    return lines


def cartridge(repo: dict, slot: int) -> str:
    W, H = 210, 146
    name = repo["name"]
    lang = (repo.get("primaryLanguage") or {}).get("name") or "—"
    lines = wrap(repo.get("description") or "", 15, W - 52, 3)
    body = [
        # shell: notch on top like a game cartridge
        f'<path d="M6 18 h40 v-10 h118 v10 h40 v{H - 24} h-198 z" fill="{BG}" stroke="{INK}" stroke-width="2"/>',
        f'<path d="M12 24 h186 v{H - 36} h-186 z" fill="url(#dots)" opacity=".35"/>',
        # label
        f'<rect x="18" y="30" width="{W - 36}" height="80" fill="{BG}" stroke="{INK}" opacity=".9"/>',
        f'<rect x="18" y="30" width="{W - 36}" height="22" fill="{VIOLET}"/>',
        f'<text x="26" y="47" class="m" font-size="16" fill="{BG}">{escape(name[:25])}</text>',
    ]
    for i, line in enumerate(lines):
        body.append(f'<text x="26" y="{70 + i * 16}" class="m" font-size="15">{escape(line)}</text>')
    body.append(f'<text x="20" y="{H - 14}" class="m acid" font-size="15">★ {repo["stargazerCount"]}</text>')
    body.append(f'<text x="{W - 20}" y="{H - 14}" class="m dim" font-size="15" text-anchor="end">{escape(lang)}</text>')
    body.append(f'<text x="{W / 2}" y="{H - 16}" class="s dim" font-size="7" text-anchor="middle">SLOT {slot}</text>')
    body.append(f'<rect x="188" y="36" width="4" height="4" fill="{ACID}" style="animation:fade 1.3s steps(2,start) {slot * 0.3}s infinite"/>')
    css = f"@keyframes insert{{from{{transform:translateY(-{H}px)}}to{{transform:none}}}}"
    return svg(W, H, f'<g style="animation:insert .5s cubic-bezier(.2,.9,.3,1) {slot * 0.12:.2f}s both">{"".join(body)}</g>', css, label=f"{name} — {repo.get('description') or ''}")


def main() -> None:
    (ASSETS / "sheet.svg").write_text(character_sheet())
    (ASSETS / "eq.svg").write_text(equalizer())
    for old in ASSETS.glob("cart-*.svg"):
        old.unlink()
    for i, repo in enumerate(STATS["featured"], 1):
        (ASSETS / f"cart-{repo['name']}.svg").write_text(cartridge(repo, i))
    for f in sorted(ASSETS.glob("*.svg")):
        print(f"{f.relative_to(ROOT)}  {f.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
