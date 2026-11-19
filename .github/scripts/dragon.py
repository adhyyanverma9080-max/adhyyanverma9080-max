"""
Tokyo Night contribution dragon (vector silhouette).

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
WAVE = 5.0                     # sideways swim amplitude in px (0 = straight lines)
WAVES_PER_COLUMN = 1.5         # how many S-bends per column sweep
PAUSE = 2.0                    # seconds of rest before the loop restarts

# ---- Tokyo Night palette ----------------------------------------------------
BG, BORDER = "#1a1b27", "#2f334d"
EMPTY = "#24283b"
LEVELS = [EMPTY, "#394b70", "#3d59a1", "#7aa2f7", "#7dcfff"]
CYAN, PURPLE, VIOLET, WHITE, MUTED = "#7dcfff", "#bb9af7", "#9d7cd8", "#c0caf5", "#565f89"

# ---- vector dragon head (faces right, origin at the neck) -------------------
def head_group():
    return (
        '<g filter="url(#glow)">'
        # horns
        f'<path d="M-3,-5 C-6,-10 -12,-11 -17,-9 C-12,-8 -8,-6 -5,-3 Z" fill="{CYAN}"/>'
        f'<path d="M0,-6 C-2,-12 -7,-14 -12,-14 C-8,-11 -4,-8 -2,-5 Z" fill="{PURPLE}"/>'
        # whiskers
        f'<path d="M14,0 C20,4 24,2 29,6" fill="none" stroke="{CYAN}" stroke-width="0.9" stroke-linecap="round"/>'
        f'<path d="M12,-2 C18,-8 22,-6 27,-10" fill="none" stroke="{CYAN}" stroke-width="0.9" stroke-linecap="round"/>'
        # skull, snout and jaw
        '<path d="M-6,-5 C-2,-7.5 6,-7.5 12,-3.5 L17.5,-2.5 C18.8,-2 18.8,0.8 17.5,1.3 L12,2 '
        'C8,5.5 0,6.5 -6,5 Z" fill="url(#headGrad)"/>'
        f'<path d="M12,1.2 L17,0.4" stroke="{BG}" stroke-width="0.7" stroke-linecap="round"/>'
        # eye
        f'<circle cx="6.5" cy="-2.2" r="1.5" fill="{WHITE}"/><circle cx="6.9" cy="-2.2" r="0.6" fill="{BG}"/>'
        '</g>'
    )


def lerp_color(a, b, t):
    a = [int(a[i:i+2], 16) for i in (1, 3, 5)]
    b = [int(b[i:i+2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


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

    # dense polyline: wavy sweeps joined by semicircular turns (exact length is measured)
    pts, col_samples = [], [[] for _ in range(cols)]
    def add(x, y, c=None):
        if pts:
            dist = pts[-1][2] + math.hypot(x - pts[-1][0], y - pts[-1][1])
        else:
            dist = 0.0
        pts.append((x, y, dist))
        if c is not None:
            col_samples[c].append((y, dist))
    for c in range(cols):
        down = c % 2 == 0
        y0, y1 = (cy(0), cy(6)) if down else (cy(6), cy(0))
        n = 44
        for i in range(n + 1):
            t = i / n
            y = y0 + (y1 - y0) * t
            # wave fades to zero at both ends so it joins the turns cleanly
            x = cx(c) + WAVE * math.sin(t * WAVES_PER_COLUMN * 2 * math.pi) * math.sin(t * math.pi)
            add(x, y, c)
        if c < cols - 1:
            m = 14
            for i in range(1, m + 1):
                a = math.pi * i / m
                x = cx(c) + R - R * math.cos(a)
                y = y1 + (R * math.sin(a) if down else -R * math.sin(a))
                add(x, y)
    total = pts[-1][2]
    path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y, _ in pts)

    travel = total / SPEED
    dur = travel + PAUSE
    f = travel / dur                      # fraction of the loop spent flying

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H}" width="{W:.0f}" height="{H}">',
         '<defs>'
         f'<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="1.6" result="b"/>'
         '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
         f'<filter id="bloom" filterUnits="userSpaceOnUse" x="0" y="0" width="{W:.0f}" height="{H}"><feGaussianBlur stdDeviation="4"/></filter>'
         f'<filter id="soft" filterUnits="userSpaceOnUse" x="0" y="0" width="{W:.0f}" height="{H}"><feGaussianBlur stdDeviation="1.4"/></filter>'
         f'<linearGradient id="headGrad" x1="0" x2="1"><stop offset="0" stop-color="{VIOLET}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>'
         f'<path id="route" d="{path}"/>'
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
            dist = min(col_samples[c], key=lambda sm: abs(sm[0] - (y + half)))[1]
            t = max((dist - 6) / SPEED / dur, 0.002)
            t2, t3 = t + 0.25 / dur, t + 0.9 / dur
            s.append(base + f'><animate attributeName="fill" calcMode="discrete" dur="{dur:.2f}s" repeatCount="indefinite" '
                     f'keyTimes="0;{t:.4f};{t2:.4f};{t3:.4f};0.995" '
                     f'values="{LEVELS[lv]};{WHITE};{PURPLE};{EMPTY};{LEVELS[lv]}"/></rect>')

    # fire trail: layered dashes (long & faint -> short & hot) travelling with the dragon
    def trail(length, width, color, opacity, flt=""):
        off = f"{length:.1f};{length - total:.1f};{length - total:.1f}"
        return (f'<use href="#route" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" '
                f'stroke-linejoin="round" opacity="{opacity}" {flt} stroke-dasharray="{length:.1f} {total + length:.1f}" '
                f'stroke-dashoffset="{length:.1f}">'
                f'<animate attributeName="stroke-dashoffset" dur="{dur:.2f}s" repeatCount="indefinite" '
                f'keyTimes="0;{f:.4f};1" values="{off}"/></use>')

    fade = (f'<animate attributeName="opacity" dur="{dur:.2f}s" repeatCount="indefinite" calcMode="discrete" '
            f'keyTimes="0;{f:.4f}" values="1;0"/>')
    # glowing aura + tapered, gradient dragon body (stacked dashes: thin tail -> thick neck)
    layers = trail(190, 15, VIOLET, 0.35, 'filter="url(#bloom)"')
    n = 9
    for i in range(n):
        t = i / (n - 1)
        length = 170 - t * 140
        layers += trail(length, 2.0 + t * 4.6, lerp_color("#6f4fc4", CYAN, t), 1)
    s.append('<g>' + fade + layers + '</g>')

    # the head, turning smoothly through every bend
    s.append(f'<g>{fade}<g>{head_group()}'
             f'<animateMotion dur="{dur:.2f}s" repeatCount="indefinite" rotate="auto" calcMode="linear" '
             f'keyPoints="0;1;1" keyTimes="0;{f:.4f};1"><mpath href="#route"/></animateMotion></g></g>')

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
