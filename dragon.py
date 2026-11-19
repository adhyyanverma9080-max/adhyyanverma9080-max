"""
Tokyo Night contribution dragon.

Pulls your real contribution calendar from GitHub and draws an animated SVG:
a pixel-art dragon flies a smooth serpentine path over the grid, leaving a
glowing purple/cyan fire trail and burning every contribution square it passes.
"""
import json, math, os, random, sys, urllib.request

USER = os.environ.get("GH_USER", "")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

# ---- layout -----------------------------------------------------------------
STEP, SIZE = 15, 12            # cell pitch / cell size (px)
PAD_X, PAD_Y = 28, 34
SPEED = 260.0                  # dragon speed in px per second
PAUSE = 2.0                    # seconds of rest before the loop restarts
PX = 1.5                       # size of one dragon "pixel"

# ---- Tokyo Night palette ----------------------------------------------------
BG, BORDER = "#1a1b27", "#2f334d"
EMPTY = "#24283b"
LEVELS = [EMPTY, "#394b70", "#3d59a1", "#7aa2f7", "#7dcfff"]
CYAN, PURPLE, VIOLET, WHITE, MUTED = "#7dcfff", "#bb9af7", "#9d7cd8", "#c0caf5", "#565f89"

# ---- pixel-art dragon (faces right). Each entry: (colour key, x1, x2, y) ----
GRID_W, GRID_H = 24, 12
BODY = [
    ("H", 18, 19, 3),                                   # horns
    ("B", 18, 21, 4),                                   # skull
    ("B", 17, 23, 5), ("E", 20, 20, 5),                 # head + eye
    ("B", 10, 22, 6), ("B", 6, 16, 7),                  # neck + back
    ("B", 5, 6, 8), ("S", 7, 14, 8), ("B", 15, 16, 8),  # belly
    ("T", 3, 4, 8), ("T", 1, 2, 9), ("S", 0, 0, 10),    # tail
    ("L", 8, 8, 9), ("L", 13, 13, 9), ("L", 8, 9, 10), ("L", 13, 14, 10),  # legs
    ("H", 7, 7, 6), ("H", 9, 9, 6),                     # back spikes
]
WING_UP = [
    ("G", 7, 7, 0), ("G", 7, 7, 1), ("W", 8, 8, 1),
    ("G", 7, 7, 2), ("W", 8, 9, 2),
    ("G", 8, 8, 3), ("W", 9, 11, 3),
    ("G", 9, 9, 4), ("W", 10, 13, 4),
    ("G", 10, 10, 5), ("W", 11, 14, 5),
]
WING_DOWN = [
    ("G", 7, 7, 4), ("W", 8, 11, 4),
    ("G", 4, 4, 5), ("W", 5, 12, 5),
    ("G", 6, 6, 6), ("W", 7, 9, 6),
]
COLORS = {"B": VIOLET, "S": CYAN, "H": CYAN, "E": WHITE, "L": VIOLET,
          "T": PURPLE, "W": PURPLE, "G": CYAN}


def sprite_rects(spec):
    out = []
    for ch, x1, x2, y in spec:
        out.append(f'<rect x="{x1*PX:.2f}" y="{y*PX:.2f}" width="{(x2-x1+1)*PX+0.15:.2f}" '
                   f'height="{PX+0.15:.2f}" fill="{COLORS[ch]}"/>')
    return "".join(out)


def dragon_group():
    w, h = GRID_W * PX, GRID_H * PX
    flap = '<animate attributeName="opacity" calcMode="discrete" dur="0.5s" repeatCount="indefinite" keyTimes="0;0.5" values="{}"/>'
    return (
        f'<g filter="url(#glow)"><g transform="translate({-w/2:.2f},{-h/2:.2f})" shape-rendering="crispEdges">'
        f'<g>{sprite_rects(WING_UP)}{flap.format("1;0")}</g>'
        f'<g>{sprite_rects(WING_DOWN)}{flap.format("0;1")}</g>'
        f'{sprite_rects(BODY)}</g></g>'
    )


# ---- data -------------------------------------------------------------------
def fetch_weeks():
    if not TOKEN:  # offline test mode
        random.seed(7)
        return [[random.choice([0, 0, 0, 1, 3, 6, 10]) for _ in range(7)] for _ in range(53)]
    q = {"query": 'query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{weeks{contributionDays{contributionCount}}}}}}',
         "variables": {"u": USER}}
    req = urllib.request.Request("https://api.github.com/graphql", json.dumps(q).encode(),
                                 {"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req))
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [[d["contributionCount"] for d in w["contributionDays"]] + [0] * (7 - len(w["contributionDays"])) for w in weeks]


def level(n, mx):
    if n == 0: return 0
    r = n / mx
    return 1 if r <= .25 else 2 if r <= .5 else 3 if r <= .75 else 4


# ---- svg --------------------------------------------------------------------
def build(weeks):
    cols = len(weeks)
    mx = max(max(w) for w in weeks) or 1
    W, H = PAD_X * 2 + cols * STEP, PAD_Y * 2 + 7 * STEP + 8
    half = SIZE / 2
    cx = lambda c: PAD_X + c * STEP + half
    cy = lambda r: PAD_Y + r * STEP + half
    R = STEP / 2
    col_len, arc_len = 6 * STEP, math.pi * R
    total = cols * col_len + (cols - 1) * arc_len

    # smooth serpentine path: straight sweeps joined by semicircular turns
    d = [f"M{cx(0):.2f},{cy(0):.2f}"]
    for c in range(cols):
        d.append(f"L{cx(c):.2f},{cy(6 if c % 2 == 0 else 0):.2f}")
        if c < cols - 1:
            d.append(f"A{R},{R} 0 0 {0 if c % 2 == 0 else 1} {cx(c+1):.2f},{cy(6 if c % 2 == 0 else 0):.2f}")
    path = " ".join(d)

    travel = total / SPEED
    dur = travel + PAUSE
    f = travel / dur                      # fraction of the loop spent flying

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H}" width="{W:.0f}" height="{H}">',
         '<defs>'
         f'<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="1.6" result="b"/>'
         '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
         f'<filter id="bloom" filterUnits="userSpaceOnUse" x="0" y="0" width="{W:.0f}" height="{H}"><feGaussianBlur stdDeviation="4"/></filter>'
         f'<filter id="soft" filterUnits="userSpaceOnUse" x="0" y="0" width="{W:.0f}" height="{H}"><feGaussianBlur stdDeviation="1.4"/></filter>'
         '</defs>',
         f'<rect x="0.5" y="0.5" width="{W-1:.0f}" height="{H-1}" rx="10" fill="{BG}" stroke="{BORDER}"/>']

    # contribution cells (they flare up and burn out as the dragon passes)
    for c, week in enumerate(weeks):
        for r, cnt in enumerate(week):
            x, y = PAD_X + c * STEP, PAD_Y + r * STEP
            lv = level(cnt, mx)
            base = f'<rect x="{x}" y="{y}" width="{SIZE}" height="{SIZE}" rx="3" fill="{LEVELS[lv]}"'
            if lv == 0:
                s.append(base + "/>")
                continue
            dist = c * (col_len + arc_len) + (r * STEP if c % 2 == 0 else (6 - r) * STEP)
            t = max((dist - 6) / SPEED / dur, 0.002)
            t2, t3 = t + 0.25 / dur, t + 0.9 / dur
            s.append(base + f'><animate attributeName="fill" calcMode="discrete" dur="{dur:.2f}s" repeatCount="indefinite" '
                     f'keyTimes="0;{t:.4f};{t2:.4f};{t3:.4f};0.995" '
                     f'values="{LEVELS[lv]};{WHITE};{PURPLE};{EMPTY};{LEVELS[lv]}"/></rect>')

    # fire trail: layered dashes (long & faint -> short & hot) travelling with the dragon
    def trail(length, width, color, opacity, flt=""):
        off = f"{length:.1f};{length - total:.1f};{length - total:.1f}"
        return (f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" '
                f'stroke-linejoin="round" opacity="{opacity}" {flt} stroke-dasharray="{length:.1f} {total + length:.1f}" '
                f'stroke-dashoffset="{length:.1f}">'
                f'<animate attributeName="stroke-dashoffset" dur="{dur:.2f}s" repeatCount="indefinite" '
                f'keyTimes="0;{f:.4f};1" values="{off}"/></path>')

    fade = (f'<animate attributeName="opacity" dur="{dur:.2f}s" repeatCount="indefinite" calcMode="discrete" '
            f'keyTimes="0;{f:.4f}" values="1;0"/>')
    s.append('<g>' + fade
             + trail(150, 11, VIOLET, 0.55, 'filter="url(#bloom)"')
             + trail(100, 7, PURPLE, 0.75, 'filter="url(#soft)"')
             + trail(62, 4.5, CYAN, 0.9, 'filter="url(#soft)"')
             + trail(30, 2.2, WHITE, 1)
             + '</g>')

    # the dragon itself, banking smoothly through every turn
    s.append(f'<g>{fade}<g>{dragon_group()}'
             f'<animateMotion dur="{dur:.2f}s" repeatCount="indefinite" rotate="auto" calcMode="linear" '
             f'keyPoints="0;1;1" keyTimes="0;{f:.4f};1" path="{path}"/></g></g>')

    s.append(f'<text x="{W/2:.0f}" y="{H-12}" font-size="10" fill="{MUTED}" text-anchor="middle" '
             f'font-family="ui-monospace,SFMono-Regular,Menlo,monospace">the dragon burns through my contributions</text>')
    s.append("</svg>")
    return "\n".join(s)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "dist"
    os.makedirs(out, exist_ok=True)
    svg = build(fetch_weeks())
    # Tokyo Night is a dark theme, so both the dark and light slots get the same image
    for name in ("github-dragon-dark.svg", "github-dragon.svg"):
        with open(os.path.join(out, name), "w", encoding="utf-8") as fh:
            fh.write(svg)
    print("done")
