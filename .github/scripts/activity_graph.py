"""Genera un gráfico SVG con las contribuciones diarias de los últimos 31 días.

Uso: python activity_graph.py <usuario> <archivo_salida.svg>
Necesita la variable de entorno GITHUB_TOKEN (la Action la pasa sola).
Con DEMO=1 usa datos de prueba y no llama a la API.
"""
import json
import os
import random
import sys
import urllib.request
from datetime import date, timedelta

DAYS = 31
W, H = 1200, 360
PAD_L, PAD_R, PAD_T, PAD_B = 70, 40, 70, 60
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch(login):
    if os.environ.get("DEMO") == "1":
        hoy = date.today()
        return [((hoy - timedelta(days=i)).isoformat(), random.choice([0, 0, 1, 2, 3, 5, 8, 12]))
                for i in range(DAYS)][::-1]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if "errors" in data or not data.get("data", {}).get("user"):
        sys.exit(f"Error de la API de GitHub: {data}")
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [(d["date"], d["contributionCount"]) for w in weeks for d in w["contributionDays"]]
    return days[-DAYS:]


def nice_max(v):
    for step in (4, 8, 12, 20, 40, 60, 100, 200, 400, 1000):
        if v <= step:
            return step
    return v


def build(login, days):
    counts = [c for _, c in days]
    total = sum(counts)
    ymax = nice_max(max(counts) or 1)
    cw = W - PAD_L - PAD_R
    ch = H - PAD_T - PAD_B
    step = cw / (len(days) - 1)

    def x(i):
        return PAD_L + i * step

    def y(v):
        return PAD_T + ch - v / ymax * ch

    pts = [(x(i), y(c)) for i, c in enumerate(counts)]
    # Curva suave (Catmull-Rom → Bézier)
    path = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, min(p1[1] + (p2[1] - p0[1]) / 6, PAD_T + ch))
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, min(p2[1] - (p3[1] - p1[1]) / 6, PAD_T + ch))
        path += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    area = path + f" L{pts[-1][0]:.1f},{PAD_T + ch} L{pts[0][0]:.1f},{PAD_T + ch} Z"

    grid = ""
    for k in range(5):
        v = ymax * k / 4
        gy = y(v)
        grid += (f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{W - PAD_R}" y2="{gy:.1f}" class="grid"/>'
                 f'<text x="{PAD_L - 14}" y="{gy + 5:.1f}" class="lbl" text-anchor="end">{int(v)}</text>')

    xlabels = ""
    for i, (d, _) in enumerate(days):
        if i % 3 == 0 or i == len(days) - 1:
            dd = date.fromisoformat(d)
            xlabels += f'<text x="{x(i):.1f}" y="{H - PAD_B + 26}" class="lbl" text-anchor="middle">{dd.day} {MESES[dd.month - 1]}</text>'

    dots = "".join(
        f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" class="dot" style="animation-delay:{0.6 + i * 0.03:.2f}s">'
        f'<title>{days[i][0]}: {counts[i]} contribuciones</title></circle>'
        for i, (px, py) in enumerate(pts))

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Contribuciones de {login} en los últimos {DAYS} días">
  <defs>
    <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#36bcf7" stop-opacity=".55"/>
      <stop offset="100%" stop-color="#36bcf7" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="reveal"><rect x="0" y="0" width="0" height="{H}"><animate attributeName="width" from="0" to="{W}" dur="1.6s" fill="freeze"/></rect></clipPath>
    <style>
      text {{ font-family: 'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif; }}
      .title {{ font-size: 22px; font-weight: 700; fill: #c0caf5; }}
      .meta {{ font-size: 15px; fill: #7aa2f7; }}
      .lbl {{ font-size: 13px; fill: #565f89; }}
      .grid {{ stroke: #24283b; stroke-width: 1; }}
      .line {{ fill: none; stroke: #36bcf7; stroke-width: 3; stroke-linecap: round; }}
      .dot {{ fill: #1a1b27; stroke: #9ece6a; stroke-width: 2.5; opacity: 0; animation: pop .4s ease-out forwards; }}
      @keyframes pop {{ to {{ opacity: 1; }} }}
    </style>
  </defs>
  <rect width="{W}" height="{H}" rx="12" fill="#1a1b27"/>
  <text x="{PAD_L}" y="40" class="title">Actividad de {login}</text>
  <text x="{W - PAD_R}" y="40" class="meta" text-anchor="end">{total} contribuciones · últimos {DAYS} días</text>
  {grid}
  <g clip-path="url(#reveal)">
    <path d="{area}" fill="url(#fill)"/>
    <path d="{path}" class="line"/>
  </g>
  {dots}
  {xlabels}
</svg>
'''


if __name__ == "__main__":
    login, out = sys.argv[1], sys.argv[2]
    days = fetch(login)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(build(login, days))
    print(f"Gráfico generado: {out} ({sum(c for _, c in days)} contribuciones)")
