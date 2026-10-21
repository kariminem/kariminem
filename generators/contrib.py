"""Fetch a GitHub user's contribution calendar + repo stats (stdlib only).

Token resolution: $GITHUB_TOKEN, else `gh auth token`. Pass cache= to reuse a JSON dump.
"""
import json
import os
import subprocess
import urllib.request

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    login
    followers { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      nodes { name stargazerCount diskUsage primaryLanguage { name color } }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel weekday } }
      }
    }
  }
}
"""

LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
          "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def _token():
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        return tok
    return subprocess.run(["gh", "auth", "token"], capture_output=True,
                          text=True, check=True).stdout.strip()


def fetch(login, cache=None):
    if cache and os.path.exists(cache):
        with open(cache) as f:
            raw = json.load(f)
    else:
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
            headers={"Authorization": f"bearer {_token()}",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = json.load(r)
        if "errors" in raw:
            raise RuntimeError(raw["errors"])
        if cache:
            with open(cache, "w") as f:
                json.dump(raw, f)
    return _normalise(raw["data"]["user"])


def _normalise(u):
    cal = u["contributionsCollection"]["contributionCalendar"]
    weeks = []
    for w in cal["weeks"]:
        weeks.append([{"date": d["date"], "count": d["contributionCount"],
                       "level": LEVELS[d["contributionLevel"]], "weekday": d["weekday"]}
                      for d in w["contributionDays"]])
    days = [d for w in weeks for d in w]
    # current + longest streak (today may still be empty, don't break the streak on it)
    longest = run = 0
    for d in days:
        run = run + 1 if d["count"] else 0
        longest = max(longest, run)
    current = 0
    for i, d in enumerate(reversed(days)):
        if d["count"]:
            current += 1
        elif i > 0:
            break
    repos = u["repositories"]["nodes"]
    langs = {}
    for r in repos:
        if r["primaryLanguage"]:
            n = r["primaryLanguage"]["name"]
            langs.setdefault(n, {"count": 0, "color": r["primaryLanguage"]["color"]})
            langs[n]["count"] += 1
    return {
        "login": u["login"], "name": u["name"] or u["login"],
        "followers": u["followers"]["totalCount"],
        "repo_count": u["repositories"]["totalCount"],
        "repos": repos,
        "stars": sum(r["stargazerCount"] for r in repos),
        "languages": dict(sorted(langs.items(), key=lambda kv: -kv[1]["count"])),
        "total": cal["totalContributions"],
        "weeks": weeks, "days": days,
        "active_days": sum(1 for d in days if d["count"]),
        "current_streak": current, "longest_streak": longest,
    }
