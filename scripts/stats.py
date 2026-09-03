#!/usr/bin/env python3
"""Generate anthracite-themed GitHub stats cards (SVG) for the profile README.

Runs in GitHub Actions with GITHUB_TOKEN; no third-party service involved.
Outputs: assets/stats-{light,dark}.svg, assets/langs-{light,dark}.svg
"""
import json, os, sys, urllib.request, datetime

LOGIN = os.environ.get("GH_LOGIN", "mikield")
TOKEN = os.environ.get("GITHUB_TOKEN")
OUT = os.environ.get("OUT_DIR", "assets")

QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions }
    }
    repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) { totalCount }
    repositories(first: 100, after: $after, ownerAffiliations: OWNER, isFork: false, orderBy: {field: STARGAZERS, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } }
      }
    }
  }
}
"""

def gql(variables):
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "profile-stats"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data: raise SystemExit(data["errors"])
    return data["data"]["user"]

def fetch():
    stars, langs, after = 0, {}, None
    while True:
        u = gql({"login": LOGIN, "after": after})
        for repo in u["repositories"]["nodes"]:
            stars += repo["stargazerCount"]
            for e in repo["languages"]["edges"]:
                langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
        pi = u["repositories"]["pageInfo"]
        if not pi["hasNextPage"]: break
        after = pi["endCursor"]
    cc = u["contributionsCollection"]
    return {
        "stars": stars,
        "commits_year": cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
        "contributions_year": cc["contributionCalendar"]["totalContributions"],
        "prs": u["pullRequests"]["totalCount"],
        "issues": u["issues"]["totalCount"],
        "followers": u["followers"]["totalCount"],
        "contributed_to": u["repositoriesContributedTo"]["totalCount"],
        "langs": langs,
    }

HIDE = {"HTML", "CSS", "SCSS", "Blade", "Shell", "Dockerfile", "Makefile"}
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
THEMES = {
    "light": dict(bg="#F3F5F7", ink="#2B2F33", sub="#5C646B", line="#D5DADF", bars=["#2B2F33", "#3A4046", "#4A535B", "#6B747C", "#8F98A0", "#B4BCC3"]),
    "dark":  dict(bg="#2B2F33", ink="#F3F5F7", sub="#A3ABB2", line="#3E444A", bars=["#F3F5F7", "#D7DCE0", "#B4BCC3", "#8F98A0", "#6B747C", "#4A535B"]),
}

def fmt(n):
    return f"{n/1000:.1f}k" if n >= 10000 else f"{n:,}"

def stats_card(d, t, w=430, h=170):
    rows = [("Stars", d["stars"]), ("Commits, last 12 months", d["commits_year"]),
            ("Pull requests", d["prs"]), ("Issues", d["issues"]), ("Contributed to", d["contributed_to"])]
    y = 62; body = ""
    for k, v in rows:
        body += (f'<text x="28" y="{y}" font-family="{FONT}" font-size="13" fill="{t["sub"]}">{k}</text>'
                 f'<text x="{w-28}" y="{y}" text-anchor="end" font-family="{MONO}" font-size="13" font-weight="700" fill="{t["ink"]}">{fmt(v)}</text>'
                 f'<line x1="28" y1="{y+8}" x2="{w-28}" y2="{y+8}" stroke="{t["line"]}" stroke-width="0.8"/>')
        y += 22
    stamp = datetime.date.today().isoformat()
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="GitHub stats">'
            f'<rect width="{w}" height="{h}" rx="14" fill="{t["bg"]}"/>'
            f'<text x="28" y="34" font-family="{FONT}" font-size="15" font-weight="700" fill="{t["ink"]}">GitHub</text>'
            f'<text x="{w-28}" y="34" text-anchor="end" font-family="{MONO}" font-size="10" fill="{t["sub"]}">updated {stamp}</text>'
            f'{body}</svg>')

def langs_card(d, t, w=330, h=170, n=6):
    items = sorted(((k, v) for k, v in d["langs"].items() if k not in HIDE), key=lambda kv: -kv[1])[:n]
    total = sum(v for _, v in items) or 1
    x, bar = 28, ""
    for i, (_, v) in enumerate(items):
        ww = (w - 56) * v / total
        bar += f'<rect x="{x:.2f}" y="50" width="{max(ww-2,0):.2f}" height="8" rx="2" fill="{t["bars"][i % len(t["bars"])]}"/>'
        x += ww
    y, leg = 86, ""
    for i, (k, v) in enumerate(items):
        cx = 28 + (i % 2) * 150; cy = y + (i // 2) * 24
        leg += (f'<rect x="{cx}" y="{cy-9}" width="9" height="9" rx="2" fill="{t["bars"][i % len(t["bars"])]}"/>'
                f'<text x="{cx+16}" y="{cy}" font-family="{FONT}" font-size="12" fill="{t["sub"]}">{k} '
                f'<tspan font-family="{MONO}" font-weight="700" fill="{t["ink"]}">{100*v/total:.0f}%</tspan></text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Top languages">'
            f'<rect width="{w}" height="{h}" rx="14" fill="{t["bg"]}"/>'
            f'<text x="28" y="34" font-family="{FONT}" font-size="15" font-weight="700" fill="{t["ink"]}">Languages</text>{bar}{leg}</svg>')

if __name__ == "__main__":
    if "--mock" in sys.argv:
        d = {"stars": 380, "commits_year": 1240, "contributions_year": 1500, "prs": 96, "issues": 41, "followers": 31, "contributed_to": 7,
             "langs": {"PHP": 620000, "TypeScript": 180000, "JavaScript": 120000, "Vue": 50000, "Go": 30000, "HTML": 90000, "CSS": 40000}}
    else:
        if not TOKEN: raise SystemExit("GITHUB_TOKEN missing")
        d = fetch()
    os.makedirs(OUT, exist_ok=True)
    for name, t in THEMES.items():
        open(f"{OUT}/stats-{name}.svg", "w").write(stats_card(d, t))
        open(f"{OUT}/langs-{name}.svg", "w").write(langs_card(d, t))
    print("stats:", {k: v for k, v in d.items() if k != "langs"})
