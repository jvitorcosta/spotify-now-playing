"""The live Spotify card of my GitHub profile README: my website's row, in the profile's purple.

The same layout as the other cards that jvitorcosta/jvitorcosta draws (scripts/lately_cards.py). While a
song plays the label reads "listening" with the website's moving ON badge; otherwise "last played".
GitHub runs CSS animations inside an image, so the badge moves in the README.
"""

from __future__ import annotations

import html
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
SANS = 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif'
THEMES = {
    "dark": dict(bg="#150d24", edge="#3b2466", ink="#efe6ff", soft="#a99bc9", accent="#b57cff", chip="#2c1b4d"),
    "light": dict(bg="#f1e8ff", edge="#820ad1", ink="#2a0845", soft="#6b4a8f", accent="#820ad1", chip="#e2d2fa"),
}
HALF, FULL, H = 420, 840, 136
YELLOW, BADGE_INK = "#ffb703", "#08130a"  # the website's ON badge
LABEL_SIZE, X = 11, 138
# The badge's three music bars: heights at each third of the loop, as on the website.
BARS = ((0.4, 1.0, 0.7), (1.0, 0.5, 0.8), (0.6, 0.9, 0.3))


@lru_cache(maxsize=1)
def _font() -> dict:
    return json.loads((HERE / "pixel_font.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _icon() -> str:
    """The inside of the 20x20 pixel Spotify tile from my website."""
    svg = (HERE / "spotify_icon.svg").read_text(encoding="utf-8")
    inner = svg[svg.index(">") + 1 : svg.rindex("</svg>")]
    return inner[inner.index("</title>") + 8 :] if "<title>" in inner else inner


def _pixel(text: str, x: float, y: float, size: float, fill: str) -> str:
    """Text in the pixel font, as paths: an image in GitHub cannot load a web font."""
    font = _font()
    scale = size / font["unitsPerEm"]
    out, advance = [], 0
    for ch in text.upper():
        path, width = font["glyphs"].get(ch, font["glyphs"][" "])
        if path:
            out.append(f'<path transform="translate({advance} 0)" d="{path}"/>')
        advance += width
    return f'<g transform="translate({x} {y}) scale({scale} {-scale})" fill="{fill}">{"".join(out)}</g>'


def _badge(x: float) -> str:
    bars = "".join(
        f'<rect class="bar b{i}" x="{x + 29 + i * 4}" y="27" width="2" height="9" fill="{BADGE_INK}"/>'
        for i in range(3)
    )
    return f'<g class="on"><rect x="{x}" y="22" width="45" height="18" fill="{YELLOW}"/>{_pixel("on", x + 5, 36, 10, BADGE_INK)}{bars}</g>'


def _styles(playing: bool) -> str:
    css = f"text{{font-family:{SANS}}}"
    if playing:
        css += ".bar{transform-box:fill-box;transform-origin:bottom;animation:.9s steps(1) infinite}"
        for i, (a, b, c) in enumerate(BARS):
            css += f".b{i}{{animation-name:bars{i}}}"
            css += (
                f"@keyframes bars{i}{{0%{{transform:scaleY({a})}}33%{{transform:scaleY({b})}}"
                f"66%{{transform:scaleY({c})}}}}"
            )
        css += "@media (prefers-reduced-motion:reduce){.bar{animation:none}}"
    return css


def _clip(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def draw(title: str, artist: str, playing: bool, picture: Optional[str], theme: str, wide: bool) -> str:
    t = THEMES.get(theme, THEMES["dark"])
    width = FULL if wide else HALF
    chars = int((width - X - 16) / 10.4)
    label = "listening" if playing else "last played"
    art = f'<rect x="16" y="16" width="104" height="104" rx="6" fill="{t["chip"]}"/>'
    if picture:
        art += (
            f'<image x="16" y="16" width="104" height="104" preserveAspectRatio="xMidYMid slice" '
            f'clip-path="url(#art)" href="{html.escape(picture)}"/>'
        )
    head = _pixel(label, X, 36, LABEL_SIZE, t["accent"])
    if playing:
        head += _badge(X + len(label) * LABEL_SIZE + 10)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{H}" viewBox="0 0 {width} {H}">\n'
        f"<title>{label.capitalize()}: {html.escape(title)}</title>\n"
        f"<style>{_styles(playing)}</style>\n"
        f'<defs><clipPath id="art"><rect x="16" y="16" width="104" height="104" rx="6"/></clipPath></defs>\n'
        f'<rect x="1.5" y="1.5" width="{width - 3}" height="{H - 3}" rx="12" fill="{t["bg"]}" '
        f'stroke="{t["edge"]}" stroke-width="2"/>\n'
        f"{art}{head}\n"
        f'<text x="{X}" y="66" font-size="19" font-weight="700" fill="{t["ink"]}">{html.escape(_clip(title, chars))}</text>\n'
        f'<text x="{X}" y="91" font-size="15" fill="{t["soft"]}">{html.escape(_clip(artist, chars + 8))}</text>\n'
        f'<svg x="{width - 46}" y="16" width="30" height="30" viewBox="0 0 20 20" shape-rendering="crispEdges">{_icon()}</svg>\n'
        "</svg>\n"
    )
