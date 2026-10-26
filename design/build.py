#!/usr/bin/env python3
"""Builds the profile README and the SVG cards it is made of.

    python3 -m pip install -r design/requirements.txt
    python3 design/build.py

Edit the copy in this file, not the generated files: README.md and assets/*.svg
are overwritten on every run. Each card is written in a dark and a light
variant, and the README picks one per viewer with <picture> and
prefers-color-scheme. GitHub serves the SVGs as images, which cannot load
external files, so the fonts (Libre Franklin, Source Serif 4, Geist Mono;
SIL OFL 1.1) are subset to the glyphs each card uses and embedded.
"""
import base64
import io
import itertools
from collections import defaultdict
from html import escape
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
ASSETS = REPO / "assets"
FONTS = HERE / "fonts"

USER = "yudistirosaputro"
RAW = f"https://raw.githubusercontent.com/{USER}/{USER}"
GH = f"https://github.com/{USER}"

W = 840          # design width of one README row
GX, GY = 8, 6    # transparent gutter around every card, so images placed side by side leave a gap
PAD = 6          # gap between the outer tray and the inner plate (the double bezel)
R = 28           # tray radius; the plate uses R - PAD so both curves share a centre
EASE = "cubic-bezier(.32,.72,0,1)"

# ---------------------------------------------------------------------------
# Copy (facts from the 2026 CV)

INTRO = (
    "I'm Yudistiro Septian Dwi Saputro, an Android engineer with 7+ years shipping Kotlin, "
    "Jetpack Compose and Flutter for banks, brokers, payments and insurers."
)
SPEC = [
    ("Currently", "Tuntun Sekuritas"),
    ("Based in", "Jakarta, Indonesia"),
    ("Focus", "Fintech · Compose · Flutter"),
]
CODE = [  # (token, role); roles: kw, str, fn, num, id, p (punctuation), None (plain)
    [("object", "kw"), (" Yudistiro ", None), ("{", "p")],
    [("    val", "kw"), (" role ", "id"), ("= ", "p"), ('"Android Engineer"', "str")],
    [("    val", "kw"), (" base ", "id"), ("= ", "p"), ('"Jakarta, Indonesia"', "str")],
    [("    val", "kw"), (" now ", "id"), ("= ", "p"), ('"Tuntun Sekuritas"', "str")],
    [("    val", "kw"), (" since ", "id"), ("= ", "p"), ("2018", "num")],
    [("    val", "kw"), (" stack ", "id"), ("= ", "p"), ("listOf", "fn"), ("(", "p"),
     ('"Kotlin"', "str"), (", ", "p"), ('"Compose"', "str"), (", ", "p"), ('"Flutter"', "str"), (")", "p")],
    [("}", "p")],
]
PREVIOUSLY = "Bank Mandiri · Stockbit · Sinarmas MSIG Life · Aino Indonesia"
STATS = [
    ("7", "+", ("Years shipping", "Android to production")),
    ("−30", "%", ("Build time,", "cut in production")),
    ("+20", "%", ("User engagement,", "lifted in production")),
]
TOOLKIT = [
    ("Android", ["Kotlin", "Jetpack Compose", "Coroutines", "Hilt", "Retrofit", "Room", "Paging 3"]),
    ("Cross-platform", ["Flutter", "Dart", "BLoC", "Dio"]),
    ("Architecture", ["Clean Architecture", "MVVM", "Unit tests", "Integration tests"]),
    ("Also", ["Firebase", "WebSocket", "Protobuf", "AI agents", "CLI tooling"]),
]
CAREER = [  # from, to, company, what
    ("2025", "now", "Tuntun Sekuritas", "Native Chart Pro, AI tooling"),
    ("2023", "2025", "Bank Mandiri", "New Smart Branch"),
    ("2021", "2023", "Stockbit", "Running Trade on WebSocket"),
    ("2020", "2021", "Sinarmas MSIG Life", "Java CRM to Flutter"),
    ("2019", "2020", "Aino Indonesia", "Payment SDK and POS"),
    ("2018", "2019", "Cipta Dinamika Unggul", "Kirim Bunga app"),
]
PROJECTS = [  # laid out two per row, in order
    dict(repo="dimock", w=520, kind="Library", lang="Kotlin", orb="sky",
         desc="Agent-native HTTP inspector and mock injector for Android. It captures OkHttp "
              "traffic on the device and lets a coding agent inject mocks to drive every UI state.",
         tags=["OkHttp", "MCP server", "Maven Central"]),
    dict(repo="palugada-cli", name="palugada", w=320, kind="CLI", lang="Rust", orb="cyan",
         tagline="“Apa lu mau, gua ada.”",
         desc="A token-cheap knowledge layer and code index for AI coding agents.",
         tags=["npm"]),
    dict(repo="SplashWallpaper", w=320, kind="App", lang="Kotlin", orb="blue",
         desc="Modular wallpaper gallery: a staggered Compose grid, Hilt and build-logic plugins.",
         tags=["Compose", "Hilt"]),
    dict(repo="movie-api", w=520, kind="App", lang="Kotlin", orb="ice",
         desc="Streaming-style TMDB movie browser with Clean Architecture, Paging 3, inline trailers "
              "and every error state reproducible with dimock.",
         tags=["Compose", "Paging 3", "Clean Architecture"]),
]
EMAIL = "yudistirosaputro@gmail.com"
LINKS = [
    ("LinkedIn", "https://www.linkedin.com/in/yudistiro15/"),
    ("Medium", "https://medium.com/@yudistirosaputro"),
    ("Email", f"mailto:{EMAIL}"),
]
QUOTE = ("“Clean code always looks like it was written by someone who cares.”", "Robert C. Martin")

# ---------------------------------------------------------------------------
# Themes

DARK = dict(
    name="dark",
    fg="#f1f6fa",
    line="#ffffff",       # tray, hairlines and chips: always drawn with an opacity
    plate="#06090d",
    tray=0.035, tray_edge=0.09, hair=0.08, chip=0.045, chip_edge=0.1,
    fg2=0.66, fg3=0.42,
    accent="#7dd3fc",
    grad=("#bae6fd", "#38bdf8"),
    syntax=dict(kw="#7dd3fc", str="#bae6fd", fn="#93c5fd", num="#7dd3fc"),
    orb=0.36,
    rim=((0, 0.16), (0.3, 0.05), (1, 0.03)),
    shadow=False,
    grid=0.09,
)
LIGHT = dict(
    name="light",
    fg="#0a1622",
    line="#000000",
    plate="#fbfdfe",
    tray=0.03, tray_edge=0.07, hair=0.08, chip=0.035, chip_edge=0.08,
    fg2=0.62, fg3=0.46,
    accent="#0369a1",
    grad=("#0284c7", "#0ea5e9"),
    syntax=dict(kw="#0369a1", str="#0e7490", fn="#1d4ed8", num="#0369a1"),
    orb=0.2,
    rim=((0, 0.07), (1, 0.05)),
    shadow=True,
    grid=0.07,
)
ORB = dict(sky="#0ea5e9", blue="#3b82f6", cyan="#06b6d4", ice="#7dd3fc", deep="#0369a1")
LANG = dict(Kotlin="#a97bff", Rust="#dea584")

# ---------------------------------------------------------------------------
# Type

FACES = {  # class: family, weight, style, file
    "text": ("Source Serif 4", 400, "normal", "source-serif-4-latin-400-normal.woff2"),
    "italic": ("Source Serif 4", 400, "italic", "source-serif-4-latin-400-italic.woff2"),
    "ui": ("Libre Franklin", 600, "normal", "libre-franklin-latin-600-normal.woff2"),
    "display": ("Libre Franklin", 700, "normal", "libre-franklin-latin-700-normal.woff2"),
    "mono4": ("Geist Mono", 400, "normal", "geist-mono-latin-400-normal.woff2"),
    "mono5": ("Geist Mono", 500, "normal", "geist-mono-latin-500-normal.woff2"),
}
STACKS = {
    "Libre Franklin": '"Libre Franklin", "Franklin Gothic", ui-sans-serif, system-ui, sans-serif',
    "Source Serif 4": '"Source Serif 4", "Iowan Old Style", Georgia, serif',
    "Geist Mono": '"Geist Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace',
}


class Type:
    def __init__(self):
        self.fonts = {k: TTFont(FONTS / f[3]) for k, f in FACES.items()}
        self.cmaps = {k: f.getBestCmap() for k, f in self.fonts.items()}
        self.embedded = {}

    def width(self, s, face, size, ls=0):
        font, cmap = self.fonts[face], self.cmaps[face]
        adv = sum(font["hmtx"][cmap.get(ord(ch), ".notdef")][0] for ch in s)
        return adv * size / font["head"].unitsPerEm + ls * len(s)

    def wrap(self, s, face, size, maxw):
        lines, cur = [], ""
        for word in s.split():
            test = f"{cur} {word}".strip()
            if cur and self.width(test, face, size) > maxw:
                lines.append(cur)
                cur = word
            else:
                cur = test
        return lines + [cur] if cur else lines

    def embed(self, face, chars):
        """A woff2 data URI holding only the glyphs in `chars`."""
        key = (face, frozenset(chars))
        if key not in self.embedded:
            font = TTFont(FONTS / FACES[face][3])
            options = subset.Options()
            options.flavor = "woff2"
            subsetter = subset.Subsetter(options)
            subsetter.populate(text="".join(sorted(chars)))
            subsetter.subset(font)
            buf = io.BytesIO()
            font.save(buf)
            self.embedded[key] = "data:font/woff2;base64," + base64.b64encode(buf.getvalue()).decode()
        return self.embedded[key]


TYPE = None

# ---------------------------------------------------------------------------
# Card


class Card:
    def __init__(self, t, w, h, title, framed=True):
        self.t, self.w, self.h, self.title, self.framed = t, w, h, title, framed
        self.need = h            # height the content asks for; a row uses the max of its cards
        self.defs, self.glows, self.items = [], [], []
        self.used = defaultdict(set)
        self._ids = itertools.count()

    # plate bounds
    @property
    def x0(self):
        return GX + PAD

    @property
    def y0(self):
        return GY + PAD

    @property
    def x1(self):
        return self.w - GX - PAD

    @property
    def y1(self):
        return self.h - GY - PAD

    def uid(self, prefix):
        return f"{prefix}{next(self._ids)}"

    def add(self, *parts, delay=None):
        body = "".join(parts)
        if delay is not None:
            body = f'<g class="rise" style="animation-delay:{delay}ms">{body}</g>'
        self.items.append(body)

    # text

    def _attrs(self, s, face, size, tone=1, color=None, ls=0):
        self.used[face].update(s)
        alpha = {1: 1, 2: self.t["fg2"], 3: self.t["fg3"]}[tone] if isinstance(tone, int) else tone
        a = f'class="{face}" font-size="{size:g}" fill="{color or self.t["fg"]}"'
        if alpha != 1:
            a += f' fill-opacity="{alpha:g}"'
        if ls:
            a += f' style="letter-spacing:{ls:g}px"'
        return a

    def text(self, x, y, s, face, size, tone=1, color=None, ls=0, anchor="start"):
        anchor = "" if anchor == "start" else f' text-anchor="{anchor}"'
        return (f'<text x="{x:g}" y="{y:g}"{anchor} {self._attrs(s, face, size, tone, color, ls)}>'
                f'{escape(s, quote=False)}</text>')

    def rich(self, x, y, runs, anchor="start"):
        """One line in several faces. runs: dicts of text() keyword arguments plus `s`."""
        anchor = "" if anchor == "start" else f' text-anchor="{anchor}"'
        spans = "".join(
            f'<tspan {self._attrs(**r)}>{escape(r["s"], quote=False)}</tspan>' for r in runs)
        return f'<text x="{x:g}" y="{y:g}"{anchor}>{spans}</text>'

    def label(self, x, y, s, anchor="start", tone=3, upper=True):
        return self.text(x, y, s.upper() if upper else s, "mono5", 9.5, tone=tone, ls=1.9, anchor=anchor)

    # shapes

    def hair(self, xa, y, xb):
        return (f'<path d="M{xa:g} {y + .5:g}H{xb:g}" stroke="{self.t["line"]}" '
                f'stroke-opacity="{self.t["hair"]:g}"/>')

    def capsule(self, x, y, w, h, fill=None, alpha=None, edge=None):
        t = self.t
        fill_attr = f'fill="{fill}"' if fill else f'fill="{t["line"]}" fill-opacity="{alpha if alpha is not None else t["chip"]:g}"'
        edge = t["chip_edge"] if edge is None else edge
        stroke = f' stroke="{t["line"]}" stroke-opacity="{edge:g}"' if edge else ""
        return (f'<rect x="{x + .5:g}" y="{y + .5:g}" width="{w - 1:g}" height="{h - 1:g}" '
                f'rx="{(h - 1) / 2:g}" {fill_attr}{stroke}/>')

    def gradient(self, xa, xb):
        gid = self.uid("g")
        a, b = self.t["grad"]
        self.defs.append(
            f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{xa:g}" y1="0" x2="{xb:g}" y2="0">'
            f'<stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>')
        return f"url(#{gid})"

    def dot(self, cx, cy, color, pulse=False):
        ring = (f'<circle class="pulse" cx="{cx:g}" cy="{cy:g}" r="3" fill="{color}"/>' if pulse else "")
        return ring + f'<circle cx="{cx:g}" cy="{cy:g}" r="3" fill="{color}"/>'

    def arrow(self, cx, cy, color, s=4.4):
        return (f'<path d="M{cx - s:g} {cy + s:g}L{cx + s:g} {cy - s:g}M{cx - s * .35:g} {cy - s:g}'
                f'H{cx + s:g}V{cy + s * .35:g}" fill="none" stroke="{color}" stroke-width="1.3" '
                f'stroke-linecap="round" stroke-linejoin="round"/>')

    def eyebrow(self, x, y, s, pulse=False):
        """The small capsule above a heading. Returns (svg, width)."""
        s = s.upper()
        tw = TYPE.width(s, "mono5", 10, 2)
        lead = 30 if pulse else 14
        w = lead + tw + 12
        parts = [self.capsule(x, y, w, 26)]
        if pulse:
            parts.append(self.dot(x + 15, y + 13, self.t["accent"], pulse=True))
        parts.append(self.text(x + lead, y + 16.6, s, "mono5", 10, tone=2, ls=2))
        return "".join(parts), w

    def chips(self, x, y, maxw, items, h=22, size=11, padx=9, gap=5, rowgap=6):
        """Flowed capsules. Returns (svg, bottom)."""
        parts, cx, cy = [], x, y
        for item in items:
            w = TYPE.width(item, "ui", size) + 2 * padx
            if cx > x and cx + w > x + maxw:
                cx, cy = x, cy + h + rowgap
            parts.append(self.capsule(cx, cy, w, h))
            parts.append(self.text(cx + w / 2, cy + h / 2 + size * .36, item, "ui", size, tone=2,
                                   anchor="middle"))
            cx += w + gap
        return "".join(parts), cy + h

    def header(self, left, right, upper=True):
        """Card title row and the full-bleed hairline under it."""
        pad = 26
        self.add(self.label(self.x0 + pad, 46, left),
                 self.label(self.x1 - pad, 46, right, anchor="end", upper=upper),
                 self.hair(self.x0, 66, self.x1))

    # background

    def orb(self, cx, cy, r, color, strength=1.0, dx=26, dy=-18, dur=18):
        gid = self.uid("o")
        self.defs.append(
            f'<radialGradient id="{gid}"><stop offset="0" stop-color="{color}" '
            f'stop-opacity="{self.t["orb"] * strength:g}"/><stop offset="1" stop-color="{color}" '
            f'stop-opacity="0"/></radialGradient>')
        self.glows.append(
            f'<circle class="drift" style="--dx:{dx}px;--dy:{dy}px;animation-duration:{dur}s" '
            f'cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="url(#{gid})"/>')

    def grid(self, cx=0.85, cy=0.0):
        """Dot texture that fades out from (cx, cy), in plate fractions."""
        pid, gid, mid = self.uid("p"), self.uid("m"), self.uid("k")
        x, y, w, h = self.x0, self.y0, self.x1 - self.x0, self.y1 - self.y0
        self.defs.append(
            f'<pattern id="{pid}" width="22" height="22" patternUnits="userSpaceOnUse">'
            f'<circle cx="11" cy="11" r=".9" fill="{self.t["line"]}" fill-opacity="{self.t["grid"]:g}"/></pattern>'
            f'<radialGradient id="{gid}" cx="{cx:g}" cy="{cy:g}" r=".8"><stop offset="0" stop-color="#fff"/>'
            f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
            f'<mask id="{mid}"><rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="url(#{gid})"/></mask>')
        self.glows.append(
            f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="url(#{pid})" mask="url(#{mid})"/>')

    # output

    def _frame(self):
        """Tray, plate and plate rim. Returns (under, over) the content."""
        t, w, h = self.t, self.w, self.h
        x, y, pw, ph = self.x0, self.y0, self.x1 - self.x0, self.y1 - self.y0
        rim = "".join(f'<stop offset="{o:g}" stop-color="{t["line"]}" stop-opacity="{a:g}"/>' for o, a in t["rim"])
        self.defs.append(
            f'<linearGradient id="rim" x1="0" y1="0" x2="0" y2="1">{rim}</linearGradient>'
            f'<clipPath id="plate"><rect x="{x:g}" y="{y:g}" width="{pw:g}" height="{ph:g}" rx="{R - PAD}"/></clipPath>')
        shadow = ""
        if t["shadow"]:
            self.defs.append(
                '<filter id="lift" x="-10%" y="-10%" width="120%" height="130%">'
                '<feDropShadow dx="0" dy="1" stdDeviation="1" flood-color="#000" flood-opacity=".05"/>'
                '<feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#000" flood-opacity=".045"/></filter>')
            shadow = ' filter="url(#lift)"'
        under = (
            f'<rect x="{GX + .5:g}" y="{GY + .5:g}" width="{w - 2 * GX - 1:g}" height="{h - 2 * GY - 1:g}" '
            f'rx="{R - .5:g}" fill="{t["line"]}" fill-opacity="{t["tray"]:g}" stroke="{t["line"]}" '
            f'stroke-opacity="{t["tray_edge"]:g}"/>'
            f'<rect x="{x:g}" y="{y:g}" width="{pw:g}" height="{ph:g}" rx="{R - PAD}" fill="{t["plate"]}"{shadow}/>'
            f'<g clip-path="url(#plate)">{"".join(self.glows)}</g>')
        over = (f'<rect x="{x + .5:g}" y="{y + .5:g}" width="{pw - 1:g}" height="{ph - 1:g}" '
                f'rx="{R - PAD - .5:g}" fill="none" stroke="url(#rim)"/>')
        return under, over

    def _style(self):
        css = []
        for face in sorted(self.used):
            family, weight, style, _ = FACES[face]
            css.append(f'@font-face{{font-family:"{family}";font-weight:{weight};font-style:{style};'
                       f'src:url({TYPE.embed(face, self.used[face])}) format("woff2")}}')
            css.append(f".{face}{{font-family:{STACKS[family]};font-weight:{weight};font-style:{style}}}")
        css += [
            "text{text-rendering:geometricPrecision}",
            f".rise{{animation:rise 1.2s {EASE} both}}",
            "@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}",
            ".drift{transform-box:fill-box;transform-origin:center;"
            "animation:drift 18s cubic-bezier(.45,.05,.25,1) infinite alternate}",
            "@keyframes drift{to{transform:translate(var(--dx),var(--dy)) scale(1.08)}}",
            f".pulse{{transform-box:fill-box;transform-origin:center;animation:pulse 2.6s {EASE} infinite}}",
            "@keyframes pulse{from{opacity:.6;transform:scale(1)}to{opacity:0;transform:scale(3.2)}}",
            "@media (prefers-reduced-motion:reduce){*{animation:none!important}}",
        ]
        return "\n".join(css)

    def svg(self):
        under, over = self._frame() if self.framed else ("", "")
        body = under + "".join(self.items) + over
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="t">'
            f'<title id="t">{escape(self.title)}</title>\n'
            f'<style>\n{self._style()}\n</style>\n'
            f'<defs>{"".join(self.defs)}</defs>\n{body}\n</svg>\n')


# ---------------------------------------------------------------------------
# Cards. Each takes a theme and a row height (0 = measure only) and sets
# card.need to the height its content asks for.


def accent_line(c, x, y, lead, word, size, ls, maxw):
    """Headline line ending in one italic serif word with the gradient. Shrinks to fit maxw."""
    serif = size * 1.1
    width = TYPE.width(lead, "display", size, ls) + TYPE.width(word, "italic", serif)
    if width > maxw:
        size, ls, serif = size * maxw / width, ls * maxw / width, serif * maxw / width
    wx = x + TYPE.width(lead, "display", size, ls)
    fill = c.gradient(wx, wx + TYPE.width(word, "italic", serif))
    return c.rich(x, y, [dict(s=lead, face="display", size=size, ls=ls),
                         dict(s=word, face="italic", size=serif, color=fill)])


def hero(t, h):
    c = Card(t, W, h or 424, "Yudistiro Saputro, Android Engineer")
    left, right = 50, W - 50
    c.orb(740, -40, 330, ORB["sky"])
    c.orb(330, 520, 320, ORB["blue"], dx=-30, dy=-22, dur=22)
    c.orb(80, 30, 210, ORB["cyan"], strength=.5, dx=20, dy=16, dur=26)
    c.grid()

    pill, _ = c.eyebrow(left, 44, "Android Engineer · Jakarta, ID", pulse=True)
    c.add(pill, delay=0)

    size, ls = 62, -2
    first = "Fintech on Android,"
    size = min(size, size * (right - left) / TYPE.width(first, "display", size, ls))
    c.add(c.text(left, 182, first, "display", size, ls=ls), delay=120)
    c.add(accent_line(c, left, 254, "built to feel ", "effortless.", size, ls, right - left), delay=220)

    lines = TYPE.wrap(INTRO, "text", 16, 440)
    c.add(*[c.text(left, 322 + i * 25, ln, "text", 16, tone=2) for i, ln in enumerate(lines)], delay=340)

    spec = []
    for i, (k, v) in enumerate(SPEC):
        y = 322 + i * 25
        if i:
            spec.append(c.hair(560, y - 17, right))
        spec += [c.label(560, y, k), c.text(right, y, v, "ui", 13.5, anchor="end")]
    c.add(*spec, delay=440)
    return c


def profile(t, h):
    c = Card(t, 520, h, "Profile: object Yudistiro")
    pad = 26
    c.orb(c.w, c.h + 40, 260, ORB["blue"], strength=.7, dur=24)
    c.header("Profile", "Yudistiro.kt", upper=False)

    num_x, code_x = c.x0 + pad, c.x0 + pad + 32
    longest = max(("".join(tok for tok, _ in line) for line in CODE), key=len)
    size = min(12, 12 * (c.x1 - pad - code_x) / TYPE.width(longest, "mono4", 12))
    syntax = t["syntax"]
    code = []
    for i, line in enumerate(CODE):
        y = 100 + i * 22
        code.append(c.text(num_x, y, f"{i + 1:02d}", "mono4", 10.5, tone=t["fg3"] * .7))
        x, runs = code_x, []
        for tok, role in line:
            lead = len(tok) - len(tok.lstrip(" "))
            tx = x + TYPE.width(" " * lead, "mono4", size)
            color = syntax.get(role)
            tone = 1 if color or role is None else (2 if role == "id" else 3)
            runs.append(c.text(tx, y, tok.strip(" "), "mono4", size, tone=tone, color=color))
            x += TYPE.width(tok, "mono4", size)
        code.append("".join(runs))
    c.add(*code, delay=120)

    y = 100 + (len(CODE) - 1) * 22 + 22
    lines = TYPE.wrap(PREVIOUSLY, "ui", 13.5, c.x1 - c.x0 - 2 * pad)
    c.add(c.hair(c.x0, y, c.x1), c.label(num_x, y + 26, "Previously"),
          *[c.text(num_x, y + 48 + i * 20, ln, "ui", 13.5, tone=2) for i, ln in enumerate(lines)],
          delay=240)
    c.need = y + 48 + (len(lines) - 1) * 20 + pad + GY + PAD
    return c


def impact(t, h):
    c = Card(t, 320, h, "Impact: 7+ years, 30% faster builds, 20% more engagement")
    pad, n = 24, len(STATS)
    c.orb(c.w + 20, c.h * .55, 220, ORB["sky"], strength=.6, dx=-20, dur=20)
    c.header("Impact", "By the numbers")
    row = max(88, (c.y1 - 66) / n) if h else 88
    for i, (value, unit, (l1, l2)) in enumerate(STATS):
        top = 66 + i * row
        mid = top + row / 2
        parts = [c.hair(c.x0 + pad, top, c.x1 - pad)] if i else []
        parts.append(c.rich(c.x0 + pad, mid + 14, [dict(s=value, face="display", size=40, ls=-1.4),
                                                  dict(s=unit, face="display", size=26, color=t["accent"])]))
        lx = c.x0 + pad + 112
        parts += [c.text(lx, mid - 3, l1, "text", 13, tone=2), c.text(lx, mid + 14, l2, "text", 13, tone=2)]
        c.add(*parts, delay=120 + i * 90)
    c.need = 66 + n * 88 + GY + PAD
    return c


def toolkit(t, h):
    c = Card(t, 320, h, "Toolkit: " + "; ".join(f"{k}: {', '.join(v)}" for k, v in TOOLKIT))
    pad = 24
    c.orb(-30, c.h + 30, 230, ORB["cyan"], strength=.6, dx=24, dy=-12, dur=23)
    c.header("Toolkit", "Daily drivers")
    y = 94
    for i, (group, items) in enumerate(TOOLKIT):
        chips, bottom = c.chips(c.x0 + pad, y + 10, c.x1 - c.x0 - 2 * pad, items)
        c.add(c.label(c.x0 + pad, y, group), chips, delay=120 + i * 80)
        y = bottom + 28
    c.need = y - 28 + pad + GY + PAD
    return c


def career(t, h):
    c = Card(t, 520, h, "Path: " + "; ".join(f"{a}–{b} {co}, {w}" for a, b, co, w in CAREER))
    pad = 26
    c.orb(c.w - 40, -40, 240, ORB["sky"], strength=.55, dx=-24, dy=18, dur=21)
    c.header("Path", f"{CAREER[-1][0]} — now")
    n = len(CAREER)
    row = max(44, (c.y1 - 66 - 8) / n) if h else 44
    for i, (start, end, company, what) in enumerate(CAREER):
        top = 66 + 4 + i * row
        y = top + row / 2 + 4.5
        parts = [c.hair(c.x0 + pad, top, c.x1 - pad)] if i else []
        current = end == "now"
        parts.append(c.rich(c.x0 + pad, y, [
            dict(s=f"{start} — ", face="mono4", size=10.5, tone=3),
            dict(s=end.upper(), face="mono5" if current else "mono4", size=10.5,
                 tone=1 if current else 3, color=t["accent"] if current else None)]))
        if current:
            parts.append(c.dot(c.x0 + pad + 112, y - 4, t["accent"], pulse=True))
        parts += [c.text(c.x0 + pad + 124, y, company, "ui", 14.5),
                  c.text(c.x1 - pad, y, what, "text", 13, tone=2, anchor="end")]
        c.add(*parts, delay=120 + i * 60)
    c.need = 66 + 8 + n * 44 + GY + PAD
    return c


def section(eyebrow, lead, word, note, size=42, h=150):
    """Unframed heading between card groups."""
    def build(t, _h):
        c = Card(t, W, h, f"{lead}{word}", framed=False)
        left, right = GX + 14, W - GX - 14
        pill, _ = c.eyebrow(left, 40, eyebrow)
        c.add(pill, delay=0)
        base = h - 34
        c.add(accent_line(c, left, base, lead, word, size, -1.4, 520), delay=100)
        lines = note if isinstance(note, list) else [note]
        c.add(*[c.text(right, base - (len(lines) - 1 - i) * 21, ln, "text", 14.5, tone=2, anchor="end")
                for i, ln in enumerate(lines)], delay=200)
        return c
    return build


def project(p):
    def build(t, h):
        c = Card(t, p["w"], h or 250, f'{p.get("name", p["repo"])}: {p["desc"]}')
        pad = 26
        left, right = c.x0 + pad, c.x1 - pad
        c.orb(c.w - 30, -20, 230, ORB[p["orb"]], strength=.8, dx=-22, dy=16, dur=19)
        lang_w = TYPE.width(p["lang"], "mono4", 10.5)
        c.add(c.label(left, 46, p["kind"]),
              f'<circle cx="{right - lang_w - 10:g}" cy="42.5" r="3.5" fill="{LANG[p["lang"]]}"/>',
              c.text(right, 46, p["lang"], "mono4", 10.5, tone=2, anchor="end"), delay=0)
        c.add(c.text(left, 100, p.get("name", p["repo"]), "display", 26, ls=-.7), delay=80)

        y = 130
        if p.get("tagline"):
            c.add(c.text(left, y, p["tagline"], "italic", 17, color=t["accent"]), delay=140)
            y += 24
        lines = TYPE.wrap(p["desc"], "text", 14, right - left)
        c.add(*[c.text(left, y + i * 20, ln, "text", 14, tone=2) for i, ln in enumerate(lines)], delay=160)
        last = y + (len(lines) - 1) * 20

        # bottom row: tags, then the repository button flush right
        mid = c.y1 - pad - 17
        wide = c.w > 400
        circle_x = right - 17
        btn = [c.capsule(right - 34, mid - 17, 34, 34, alpha=t["chip"] * .8)] if not wide else []
        if wide:
            tw = TYPE.width("Repository", "ui", 12)
            bw = 16 + tw + 10 + 26 + 4
            btn.append(c.capsule(right - bw, mid - 17, bw, 34))
            btn.append(c.text(right - bw + 16, mid + 4.3, "Repository", "ui", 12))
            circle_x = right - 4 - 13
            stop = right - bw - 10
        else:
            stop = right - 34 - 10
        btn.append(f'<circle cx="{circle_x:g}" cy="{mid:g}" r="13" fill="{t["line"]}" fill-opacity="{t["chip"] * 1.8:g}"/>')
        btn.append(c.arrow(circle_x, mid, t["fg"], 3.6))
        tags = []
        for n in range(len(p["tags"]), 0, -1):
            if left + sum(TYPE.width(x, "ui", 11) + 23 for x in p["tags"][:n]) - 5 <= stop:
                tags = [c.chips(left, mid - 11, 9999, p["tags"][:n])[0]]
                break
        c.add(*tags, *btn, delay=240)
        c.need = max(250, last + 92)
        return c
    return build


def contact(t, h):
    c = Card(t, W, h or 254, f"Contact: {EMAIL}")
    left, right = 50, W - 50
    c.orb(760, 300, 330, ORB["sky"], dx=-30, dy=-20, dur=20)
    c.orb(120, -60, 260, ORB["blue"], strength=.7, dx=24, dy=20, dur=24)
    c.grid(cx=.95, cy=1)
    pill, _ = c.eyebrow(left, 44, "Contact", pulse=True)
    c.add(pill, delay=0)
    size, ls = 44, -1.6
    c.add(c.text(left, 140, "Got a hard Android problem?", "display", size, ls=ls), delay=100)
    c.add(accent_line(c, left, 196, "Let's ", "talk it through.", size, ls, 500), delay=180)
    c.add(c.label(right, 170, "Email", anchor="end"), c.text(right, 196, EMAIL, "ui", 15, anchor="end"),
          delay=260)
    return c


def button(label, primary, width):
    def build(t, h):
        c = Card(t, width, 76, label, framed=False)
        x, y, w, hh = GX, GY, width - 2 * GX, 64
        inner = (x + 5, y + 5, w - 10, hh - 10)
        face_fill = t["fg"] if primary else t["plate"]
        ink = t["plate"] if primary else t["fg"]
        cx, cy = inner[0] + inner[2] - 5 - 18, y + hh / 2
        c.add(c.capsule(x, y, w, hh, alpha=t["tray"], edge=t["tray_edge"]),
              f'<rect x="{inner[0]:g}" y="{inner[1]:g}" width="{inner[2]:g}" height="{inner[3]:g}" '
              f'rx="{inner[3] / 2:g}" fill="{face_fill}"/>',
              c.text(inner[0] + 24, cy + 5.3, label, "ui", 15, color=ink),
              f'<circle cx="{cx:g}" cy="{cy:g}" r="18" fill="{ink}" fill-opacity=".09"/>',
              c.arrow(cx, cy, ink, 4.2), delay=0)
        return c
    return build


def footer(t, h):
    c = Card(t, W, 132, f"{QUOTE[0]} — {QUOTE[1]}", framed=False)
    c.add(c.text(W / 2, 64, QUOTE[0], "italic", 21, tone=2, anchor="middle"), delay=0)
    c.add(c.label(W / 2, 94, f"— {QUOTE[1]}", anchor="middle"), delay=120)
    return c


# ---------------------------------------------------------------------------
# README


def rows():
    """[(asset name, builder, link, alt)] per README line; None marks the contribution snake."""
    work = section("Selected work", "Things I've built ", "lately.",
                   ["Open-source libraries, CLIs and apps,", "mostly Kotlin and sometimes Rust."])
    activity = section("Activity", "Shipping, ", "one square at a time.", "Redrawn daily by GitHub Actions",
                       size=32, h=146)
    projects = [(f"project-{p['repo'].lower()}", project(p), f"{GH}/{p['repo']}",
                 f'{p.get("name", p["repo"])} ({p["kind"]}, {p["lang"]}): {p["desc"]}') for p in PROJECTS]
    width = W // len(LINKS)
    return [
        [("hero", hero, None, f"Yudistiro Saputro, Android Engineer in Jakarta. {INTRO}")],
        [("profile", profile, None, "Android Engineer at Tuntun Sekuritas, Jakarta, since 2018. "
                                    f"Previously {PREVIOUSLY.replace(' · ', ', ')}."),
         ("impact", impact, None, "7+ years shipping Android; build time cut 30% and engagement up 20% in production.")],
        [("toolkit", toolkit, None, "; ".join(f"{k}: {', '.join(v)}" for k, v in TOOLKIT)),
         ("path", career, None, "; ".join(f"{a}–{b}: {co}, {w}" for a, b, co, w in CAREER))],
        [("work", work, None, "Selected work")],
        projects[:2],
        projects[2:],
        [("activity", activity, None, "Activity")],
        None,
        [("contact", contact, None, f"Got a hard Android problem? Let's talk it through. {EMAIL}")],
        [(f"link-{label.lower()}", button(label, i == 0, width), url, label)
         for i, (label, url) in enumerate(LINKS)],
        [("footer", footer, None, f"{QUOTE[0]} — {QUOTE[1]}")],
    ]


def picture(name, width, alt):
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="{RAW}/main/assets/{name}-dark.svg">'
            f'<img src="{RAW}/main/assets/{name}-light.svg" width="{width}" alt="{escape(alt)}"></picture>')


def snake():
    base = f"{RAW}/output/github-contribution-grid-snake"
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="{base}-dark.svg">'
            f'<img src="{base}.svg" width="98%" alt="Contribution graph being eaten by a snake"></picture>')


def main():
    global TYPE
    TYPE = Type()
    ASSETS.mkdir(exist_ok=True)
    for old in ASSETS.glob("*.svg"):
        old.unlink()
    lines = []
    for row in rows():
        if row is None:
            lines.append(snake() + "<br>")  # the extra break is breathing room before the contact card
            continue
        cells = []
        for theme in (DARK, LIGHT):
            h = max(build(theme, 0).need for _, build, _, _ in row)
            for name, build, _, _ in row:
                card = build(theme, h)
                (ASSETS / f"{name}-{theme['name']}.svg").write_text(card.svg())
        for name, build, link, alt in row:
            share = build(DARK, 0).w / W * 100
            width = "100%" if share == 100 else f"{int(share * 100) / 100 - .01:.2f}%"
            cell = picture(name, width, alt)
            cells.append(f'<a href="{link}">{cell}</a>' if link else cell)
        lines.append("".join(cells))

    readme = (
        "<!--\n"
        "  Generated by design/build.py. Edit the copy there, then run:\n"
        "    python3 -m pip install -r design/requirements.txt && python3 design/build.py\n"
        "-->\n\n"
        '<p align="center">\n' + "<br>\n".join(lines) + "\n</p>\n")
    (REPO / "README.md").write_text(readme)
    print(f"wrote README.md and {len(list(ASSETS.glob('*.svg')))} cards to {ASSETS.relative_to(REPO)}/")


if __name__ == "__main__":
    main()
