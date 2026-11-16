#!/usr/bin/env python3
"""Fetch the GitHub data the cards need and store it in data/*.json.

Uses the GitHub GraphQL API. In GitHub Actions the built-in GITHUB_TOKEN
is enough for public data. Locally: GITHUB_TOKEN=$(gh auth token) python scripts/fetch_data.py
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!, $prq: String!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false,
                 first: 6, orderBy: {field: STARGAZERS, direction: DESC}) {
      nodes { name description stargazerCount url primaryLanguage { name color } }
    }
  }
  prs: search(query: $prq, type: ISSUE, first: 30) {
    issueCount
    nodes {
      ... on PullRequest {
        title url mergedAt
        repository { nameWithOwner stargazerCount }
      }
    }
  }
}
"""


def graphql(token: str, variables: dict) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload["data"]


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN missing", file=sys.stderr)
        return 1
    profile = json.loads((DATA / "profile.json").read_text())
    login = profile["username"]
    now = datetime.now(timezone.utc)
    data = graphql(token, {
        "login": login,
        "from": (now - timedelta(days=365)).isoformat(),
        "to": now.isoformat(),
        # merged PRs to repositories you don't own = open-source contributions
        "prq": f"author:{login} is:pr is:merged -user:{login} sort:updated-desc",
    })

    cal = data["user"]["contributionsCollection"]["contributionCalendar"]
    days = [
        {"date": d["date"], "count": d["contributionCount"]}
        for w in cal["weeks"] for d in w["contributionDays"]
    ]
    (DATA / "contributions.json").write_text(json.dumps({
        "updated": now.strftime("%Y-%m-%d"),
        "total": cal["totalContributions"],
        "days": days,
    }, indent=1))

    prs = [
        {
            "repo": n["repository"]["nameWithOwner"],
            "stars": n["repository"]["stargazerCount"],
            "title": n["title"],
            "url": n["url"],
            "merged": (n.get("mergedAt") or "")[:10],
        }
        for n in data["prs"]["nodes"] if n
    ]
    (DATA / "oss.json").write_text(json.dumps({
        "total_merged": data["prs"]["issueCount"], "prs": prs}, indent=1))

    repos = [
        {
            "name": r["name"], "description": r["description"] or "",
            "stars": r["stargazerCount"], "url": r["url"],
            "language": (r["primaryLanguage"] or {}).get("name"),
            "color": (r["primaryLanguage"] or {}).get("color"),
        }
        for r in data["user"]["repositories"]["nodes"]
    ]
    (DATA / "repos.json").write_text(json.dumps(repos, indent=1))
    print(f"ok: {cal['totalContributions']} contributions, {len(prs)} merged PRs, {len(repos)} repos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
