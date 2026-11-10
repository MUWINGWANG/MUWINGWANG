"""Generate a stats card SVG that includes private-repo activity.

Needs a token that can read the private repos (STATS_TOKEN); with the default
GITHUB_TOKEN only public activity is visible.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from html import escape

USER = os.environ["GH_USER"]
TOKEN = os.environ["GH_TOKEN"]
OUT = sys.argv[1] if len(sys.argv) > 1 else "stats/stats.svg"


def request(url, body=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body else None,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "stats-card",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def search_count(kind, query):
    q = urllib.parse.quote(query)
    return request(f"https://api.github.com/search/{kind}?q={q}&per_page=1")["total_count"]


def fetch_user():
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection { contributionCalendar { totalContributions } }
        repositoriesContributedTo(includeUserRepositories: true,
          contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) { totalCount }
        repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC) {
          nodes { stargazerCount }
        }
      }
    }"""
    data = request("https://api.github.com/graphql", {"query": query, "variables": {"login": USER}})
    return data["data"]["user"]


user = fetch_user()
rows = [
    ("Contributions (last year)", user["contributionsCollection"]["contributionCalendar"]["totalContributions"]),
    ("Total Commits", search_count("commits", f"author:{USER}")),
    ("Total PRs", search_count("issues", f"author:{USER} type:pr")),
    ("Total Issues", search_count("issues", f"author:{USER} type:issue")),
    ("Total Stars", sum(r["stargazerCount"] for r in user["repositories"]["nodes"])),
    ("Contributed to", user["repositoriesContributedTo"]["totalCount"]),
]

LINE_H = 30
height = 70 + LINE_H * len(rows)
items = "\n".join(
    f'  <text x="30" y="{80 + i * LINE_H}" class="label">{escape(label)}</text>'
    f'<text x="310" y="{80 + i * LINE_H}" class="value">{value}</text>'
    for i, (label, value) in enumerate(rows)
)

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="360" height="{height}" viewBox="0 0 360 {height}">
  <style>
    .title {{ font: 600 22px 'Segoe UI', Ubuntu, sans-serif; fill: #58a6ff; }}
    .label {{ font: 400 15px 'Segoe UI', Ubuntu, sans-serif; fill: #8b949e; }}
    .value {{ font: 600 15px 'Segoe UI', Ubuntu, sans-serif; fill: #c9d1d9; text-anchor: end; }}
  </style>
  <rect x="0.5" y="0.5" rx="6" width="359" height="{height - 1}" fill="#0d1117" stroke="#30363d"/>
  <text x="30" y="42" class="title">Stats</text>
{items}
</svg>
"""

os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
with open(OUT, "w") as f:
    f.write(svg)
print(dict(rows))
