"""Pull profile stats from the GitHub GraphQL API into data/stats.json.

Needs GITHUB_TOKEN in the environment. Stdlib only, so it runs bare in Actions.
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "data" / "config.json").read_text())
LOGIN = CONFIG["login"]
TOKEN = os.environ.get("GITHUB_TOKEN") or sys.exit("GITHUB_TOKEN is not set")


def gql(query: str, variables: dict) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        body = json.load(r)
    if body.get("errors"):
        sys.exit(f"GraphQL errors: {body['errors']}")
    return body["data"]


USER_Q = """
query($login:String!, $after:String) {
  user(login:$login) {
    name login createdAt
    followers { totalCount }
    repositories(ownerAffiliations:OWNER, first:100, after:$after, orderBy:{field:PUSHED_AT, direction:DESC}) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes {
        name description url stargazerCount isFork isPrivate isArchived pushedAt
        primaryLanguage { name color }
        languages(first:10, orderBy:{field:SIZE, direction:DESC}) { edges { size node { name color } } }
      }
    }
  }
}"""

CALENDAR_Q = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      totalCommitContributions totalPullRequestContributions totalIssueContributions
      totalPullRequestReviewContributions restrictedContributionsCount
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
  }
}"""


def fetch_user() -> tuple[dict, list[dict]]:
    repos, after, user = [], None, None
    while True:
        data = gql(USER_Q, {"login": LOGIN, "after": after})["user"]
        user = user or data
        page = data["repositories"]
        repos += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]
    return user, repos


def fetch_days(created: dt.datetime, now: dt.datetime) -> tuple[dict[str, int], dict]:
    """every contribution day since the account was created, plus the trailing-12-month collection"""
    days: dict[str, int] = {}
    last = None
    start = created
    while start < now:
        end = min(start + dt.timedelta(days=365), now)
        cc = gql(CALENDAR_Q, {"login": LOGIN, "from": start.isoformat(), "to": end.isoformat()})["user"]["contributionsCollection"]
        for w in cc["contributionCalendar"]["weeks"]:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]
        last = cc
        start = end
    # the API aligns ranges to whole weeks, so re-query exactly the trailing year for clean totals
    year = gql(CALENDAR_Q, {"login": LOGIN, "from": (now - dt.timedelta(days=365)).isoformat(), "to": now.isoformat()})
    return days, year["user"]["contributionsCollection"]


def streaks(days: dict[str, int], today: dt.date) -> dict:
    dates = sorted(days)
    longest = cur = 0
    longest_range = cur_range = (None, None)
    prev = None
    for d in dates:
        day = dt.date.fromisoformat(d)
        if days[d] > 0:
            if prev is not None and (day - prev).days == 1 and cur:
                cur += 1
                cur_range = (cur_range[0], d)
            else:
                cur, cur_range = 1, (d, d)
            if cur > longest:
                longest, longest_range = cur, cur_range
        else:
            cur, cur_range = 0, (None, None)
        prev = day
    # current streak: still alive if the last counted day is today or yesterday
    current, current_range = 0, (None, None)
    if cur_range[1] and (today - dt.date.fromisoformat(cur_range[1])).days <= 1:
        current, current_range = cur, cur_range
    return {
        "current": current, "current_start": current_range[0], "current_end": current_range[1],
        "longest": longest, "longest_start": longest_range[0], "longest_end": longest_range[1],
    }


def languages(repos: list[dict], months: int) -> list[dict]:
    """bytes per language across non-fork repos pushed in the last `months` months"""
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30 * months)).isoformat()
    skip = set(CONFIG.get("ignore_languages", []))
    totals: dict[str, dict] = {}
    for r in repos:
        if r["isFork"] or r["isArchived"] or r["pushedAt"] < cutoff:
            continue
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            if n in skip:
                continue
            t = totals.setdefault(n, {"name": n, "color": e["node"]["color"], "bytes": 0})
            t["bytes"] += e["size"]
    out = sorted(totals.values(), key=lambda t: -t["bytes"])
    total = sum(t["bytes"] for t in out) or 1
    for t in out:
        t["pct"] = round(100 * t["bytes"] / total, 1)
    return out[: CONFIG.get("language_count", 6)]


def main() -> None:
    now = dt.datetime.now(dt.timezone.utc)
    today = now.date()
    user, repos = fetch_user()
    created = dt.datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))
    days, year = fetch_days(created, now)

    public = [r for r in repos if not r["isPrivate"]]
    by_name = {r["name"]: r for r in repos}
    featured = []
    for name in CONFIG["featured"]:
        r = by_name.get(name)
        if r and not r["isPrivate"]:
            featured.append({k: r[k] for k in ("name", "description", "url", "stargazerCount", "primaryLanguage", "pushedAt")})

    # trailing 52 full weeks + the current partial week, as [date, count] lists
    weeks = [[[d["date"], d["contributionCount"]] for d in w["contributionDays"]] for w in year["contributionCalendar"]["weeks"]]
    week_totals = [sum(c for _, c in w) for w in weeks]

    stats = {
        "generated_at": now.isoformat(timespec="seconds"),
        "user": {"login": user["login"], "name": user["name"], "created_at": user["createdAt"], "followers": user["followers"]["totalCount"]},
        "totals": {
            "contributions_all_time": sum(days.values()),
            "contributions_12mo": year["contributionCalendar"]["totalContributions"],
            "commits_12mo": year["totalCommitContributions"],
            "prs_12mo": year["totalPullRequestContributions"],
            "reviews_12mo": year["totalPullRequestReviewContributions"],
            "private_12mo": year["restrictedContributionsCount"],
            "stars": sum(r["stargazerCount"] for r in repos),
            "repos": user["repositories"]["totalCount"],
            "repos_public": len(public),
        },
        "streak": streaks(days, today),
        "weeks": weeks,
        "best_week": max(week_totals),
        "this_week": week_totals[-1],
        "languages": languages(repos, CONFIG.get("language_months", 24)),
        "featured": featured,
    }
    out = ROOT / "data" / "stats.json"
    out.write_text(json.dumps(stats, indent=1) + "\n")
    t = stats["totals"]
    print(f"{out}: {t['contributions_12mo']} contributions / 12mo ({t['private_12mo']} private), "
          f"streak {stats['streak']['current']}d (best {stats['streak']['longest']}d), {t['stars']}★")


if __name__ == "__main__":
    main()
