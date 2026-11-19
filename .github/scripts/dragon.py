"""Builds an animated 'dragon eats your contribution graph' SVG from real GitHub data."""
import json, os, random, sys, urllib.request

USER = os.environ.get("GH_USER", "")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
STEP, SIZE, PAD_X, PAD_Y = 15, 12, 20, 30
STEP_TIME = 0.06  # seconds per cell

def fetch_weeks():
    if not TOKEN:  # offline test mode
        random.seed(1)
        return [[random.choice([0, 0, 1, 3, 6, 10]) for _ in range(7)] for _ in range(53)]
    q = {"query": 'query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{weeks{contributionDays{contributionCount}}}}}}',
         "variables": {"u": USER}}
    req = urllib.request.Request("https://api.github.com/graphql", json.dumps(q).encode(),
                                 {"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req))
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    out = []
    for w in weeks:
        days = [d["contributionCount"] for d in w["contributionDays"]]
        out.append(days + [0] * (7 - len(days)))
    return out

def level(n, mx):
    if n == 0: return 0
    r = n / mx
    return 1 if r <= .25 else 2 if r <= .5 else 3 if r <= .75 else 4

def build(weeks, theme):
    pal = {"dark": ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
           "light": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]}[theme]
    bg = "#0d1117" if theme == "dark" else "#ffffff"
    mx = max(max(w) for w in weeks) or 1
    cols = len(weeks)
    W, H = PAD_X * 2 + cols * STEP, PAD_Y * 2 + 7 * STEP + 10
    # zigzag path: down one column, up the next
    path = []
    for c in range(cols):
        rows = range(7) if c % 2 == 0 else range(6, -1, -1)
        path += [(c, r) for r in rows]
    n = len(path)
    total = n * STEP_TIME + 2.0
    order = {p: i for i, p in enumerate(path)}
    def pos(p): return PAD_X + p[0] * STEP, PAD_Y + p[1] * STEP

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
         f'<rect width="100%" height="100%" fill="{bg}" rx="8"/>']
    for c, w in enumerate(weeks):
        for r, cnt in enumerate(w):
            x, y = pos((c, r))
            lv = level(cnt, mx)
            if lv == 0:
                s.append(f'<rect x="{x}" y="{y}" width="{SIZE}" height="{SIZE}" rx="2" fill="{pal[0]}"/>')
            else:
                t = (order[(c, r)] + 1) * STEP_TIME / total
                s.append(f'<rect x="{x}" y="{y}" width="{SIZE}" height="{SIZE}" rx="2" fill="{pal[lv]}">'
                         f'<animate attributeName="fill" calcMode="discrete" dur="{total:.2f}s" repeatCount="indefinite" '
                         f'keyTimes="0;{t:.4f};0.99" values="{pal[lv]};{pal[0]};{pal[lv]}"/></rect>')
    def mover(glyph, shift, size, dx, dy):
        pts = [path[min(i + shift, n - 1)] for i in range(n)]
        vals = ";".join(f"{pos(p)[0] + dx},{pos(p)[1] + dy}" for p in pts)
        kt = ";".join(f"{(i * STEP_TIME) / total:.4f}" for i in range(n))
        return (f'<text font-size="{size}" text-anchor="middle">{glyph}'
                f'<animateTransform attributeName="transform" type="translate" calcMode="discrete" '
                f'dur="{total:.2f}s" repeatCount="indefinite" keyTimes="{kt}" values="{vals}"/></text>')
    s.append(mover("🔥", 2, 13, 6, 11))   # fire breath, a little ahead
    s.append(mover("🐉", 0, 24, 6, 18))   # the dragon
    s.append(f'<text x="{W/2}" y="{H-10}" font-size="10" fill="{pal[3]}" text-anchor="middle" '
             f'font-family="monospace">the dragon eats my contributions — go commit more 🐲</text>')
    s.append("</svg>")
    return "\n".join(s)

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "dist"
    os.makedirs(out, exist_ok=True)
    weeks = fetch_weeks()
    for t in ("dark", "light"):
        open(f"{out}/github-dragon{'-dark' if t == 'dark' else ''}.svg", "w", encoding="utf-8").write(build(weeks, t))
    print("done")
