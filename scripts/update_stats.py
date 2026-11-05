#!/usr/bin/env python3
"""Regenerate the contribution stats in README.md and assets/stats.svg.

Counts public pull requests only, read through the `gh` CLI.

merged     merged into the repository's default branch
backports  on any other branch, opened by me or carrying a commit of mine,
           whoever opened it. GitHub search cannot filter by commit author,
           so these come from the cross-references of my merged pull requests.
open       still open, backports included
"""
import html
import json
import re
import subprocess
from pathlib import Path

ME = "TheArkadiuszGrzelka"
ROOT = Path(__file__).resolve().parent.parent
START = "<!-- stats:start -->"
END = "<!-- stats:end -->"
SEARCH_CAP = 1000
LTS_BRANCHES = {"v3.7-branch"}

# Own organizations are not upstream work; dts2repl was dropped from the profile on purpose.
EXCLUDED = "-user:TheArkadiuszGrzelka -user:ArivEmb -user:Flowtly-PSA -user:Dev-IT-Wise -repo:antmicro/dts2repl"

# A repository missing here still gets a row, named after the repository.
PROJECTS = {
    "zephyrproject-rtos/zephyr": (
        "Zephyr RTOS",
        "Microchip PIC32CZ CA and PIC32CM SG/GC bring-up, STM32H5 USB, display and touch, "
        "Efinix Sapphire, Bluetooth LE Audio and ISO, audio codec drivers, MCUmgr, "
        "hardened network parsers with libFuzzer harnesses",
    ),
    "zephyrproject-rtos/hal_microchip": (
        "Zephyr Microchip HAL",
        "Register mappings for PIC32C and SAM peripherals: SERCOM, USART, SPI, USB, RTC",
    ),
    "mcu-tools/mcuboot": ("MCUboot", "Serial recovery robustness, RISC-V boot fixes, simulator coverage"),
    "google/bumble": ("Google Bumble", "LE Audio ISO and BIG sync handling, SMP pairing correctness, serial resync"),
    "lvgl/lvgl": (
        "LVGL",
        "STM32 display drivers: LTDC D-cache on Cortex-M55, HAL callbacks, NemaGFX pool sizing, DMA2D and canvas",
    ),
    "nrfconnect/sdk-nrf": ("nRF Connect SDK", "nRF Audio: codec integration and audio clock drift, MPSL in simulation"),
    "square/pylink": ("pylink", "J-Link version detection from the library file name"),
    "renode/renode-infrastructure": ("Renode", "Peripheral models: STM32H5 FDCAN"),
    "nordicsemi/nrfx": ("nrfx", "nRF5340 MDK: barrier after the UICR NFCPINS write"),
}

SEARCH_QUERY = """
query($q: String!, $cursor: String) {
  search(query: $q, type: ISSUE, first: 100, after: $cursor) {
    issueCount
    pageInfo { hasNextPage endCursor }
    nodes { ... on PullRequest {
      number title url state baseRefName
      repository { nameWithOwner defaultBranchRef { name } }
    } }
  }
}"""

CROSS_REFERENCES_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      timelineItems(first: 100, itemTypes: [CROSS_REFERENCED_EVENT]) {
        nodes { ... on CrossReferencedEvent { source { ... on PullRequest {
          number title url state baseRefName
          repository { nameWithOwner }
          commits(first: 100) { nodes { commit { authors(first: 5) { nodes { user { login } } } } } }
        } } } }
      }
    }
  }
}"""


def graphql(query, **variables):
    command = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        command += ["-F" if isinstance(value, int) else "-f", f"{key}={value}"]
    return json.loads(subprocess.run(command, check=True, capture_output=True, text=True).stdout)["data"]


def check_search_cap(count):
    if count >= SEARCH_CAP:
        raise RuntimeError(f"search matched {count} pull requests, over the cap of {SEARCH_CAP}: counts would be short")


def fetch_authored(author):
    query = f"is:pr is:public author:{author} {EXCLUDED}"
    authored, cursor = [], None
    while True:
        variables = {"q": query, **({"cursor": cursor} if cursor else {})}
        search = graphql(SEARCH_QUERY, **variables)["search"]
        check_search_cap(search["issueCount"])
        for node in search["nodes"]:
            authored.append({
                "repo": node["repository"]["nameWithOwner"],
                "number": node["number"],
                "title": node["title"],
                "url": node["url"],
                "state": node["state"],
                "base": node["baseRefName"],
                "default": node["repository"]["defaultBranchRef"]["name"],
                "logins": [],
            })
        if not search["pageInfo"]["hasNextPage"]:
            return authored
        cursor = search["pageInfo"]["endCursor"]


def fetch_candidates(authored):
    """Pull requests in the same repository that reference one of my merged ones."""
    candidates = []
    for source in authored:
        if source["state"] != "MERGED" or source["base"] != source["default"]:
            continue
        owner, name = source["repo"].split("/")
        data = graphql(CROSS_REFERENCES_QUERY, owner=owner, name=name, number=source["number"])
        for event in data["repository"]["pullRequest"]["timelineItems"]["nodes"]:
            ref = event.get("source") or {}
            if ref.get("repository", {}).get("nameWithOwner") != source["repo"]:
                continue
            candidates.append({
                "repo": source["repo"],
                "number": ref["number"],
                "title": ref["title"],
                "url": ref["url"],
                "state": ref["state"],
                "base": ref["baseRefName"],
                "default": source["default"],
                "logins": [
                    author["user"]["login"]
                    for node in ref["commits"]["nodes"]
                    for author in node["commit"]["authors"]["nodes"]
                    if author["user"]
                ],
            })
    return candidates


def summarize(authored, candidates, me):
    """Per-repository counts; a pull request is counted once however often it is seen."""
    backports = {}
    for pr in authored:
        if pr["base"] != pr["default"]:
            backports[pr["repo"], pr["number"]] = pr
    for pr in candidates:
        if pr["base"] != pr["default"] and me in pr["logins"]:
            backports[pr["repo"], pr["number"]] = pr

    summary = {}
    for pr in authored:
        summary.setdefault(pr["repo"], {"default": pr["default"], "merged": 0, "open": 0, "backports": [], "merged_backports": []})
    for pr in authored:
        if pr["base"] == pr["default"]:
            summary[pr["repo"]]["merged"] += pr["state"] == "MERGED"
            summary[pr["repo"]]["open"] += pr["state"] == "OPEN"
    for pr in backports.values():
        stats = summary[pr["repo"]]
        if pr["state"] == "CLOSED":
            continue
        stats["backports"].append(pr)
        if pr["state"] == "MERGED":
            stats["merged_backports"].append(pr)
        else:
            stats["open"] += 1
    return summary


def branch_key(branch):
    return [int(part) for part in re.findall(r"\d+", branch)] or [0]


def branch_label(branch):
    name = branch.removesuffix("-branch")
    return f"{name} LTS" if branch in LTS_BRANCHES else name


def totals(summary):
    merged_backports = [pr for stats in summary.values() for pr in stats["merged_backports"]]
    return {
        "merged": sum(stats["merged"] for stats in summary.values()),
        "backports": len(merged_backports),
        "open": sum(stats["open"] for stats in summary.values()),
        "projects": len(summary),
        "branches": [branch_label(b) for b in sorted({pr["base"] for pr in merged_backports}, key=branch_key)],
    }


def pulls_link(repo, author, qualifier, count):
    return f"[{count}](https://github.com/{repo}/pulls?q=is%3Apr+author%3A{author}+{qualifier})"


def render_stats_block(summary, author):
    rows = sorted(summary, key=lambda r: (-summary[r]["merged"] - len(summary[r]["merged_backports"]), r))
    lines = ["| Project | Focus | Merged | Backports | Open |", "|---|---|--:|--:|--:|"]
    for repo in rows:
        stats = summary[repo]
        name, focus = PROJECTS.get(repo, (repo, ""))
        merged = pulls_link(repo, author, f"is%3Amerged+base%3A{stats['default']}", stats["merged"])
        opened = pulls_link(repo, author, "is%3Aopen", stats["open"])
        backports = len(stats["merged_backports"])
        lines.append(f"| [{name}](https://github.com/{repo}) | {focus} | {merged} | {backports or '-'} | {opened} |")

    # A backport keeps the title of the fix, so the title groups the branches of one fix.
    fixes = {}
    for repo in rows:
        for pr in summary[repo]["backports"]:
            title = re.sub(r"^\[backport [^\]]*\]\s*", "", pr["title"], flags=re.IGNORECASE)
            fixes.setdefault((repo, title), []).append(pr)
    if fixes:
        lines += ["", "<details>", "<summary><b>Backports to release branches</b></summary>", ""]
        for (repo, title), prs in sorted(fixes.items()):
            links = " ".join(
                f"[{branch_label(pr['base'])}{'' if pr['state'] == 'MERGED' else ' (open)'}]({pr['url']})"
                for pr in sorted(prs, key=lambda pr: branch_key(pr["base"]))
            )
            lines.append(f"- {html.escape(title, quote=False)}: {links}")
        lines += ["", "</details>"]
    return "\n".join(lines)


def render_stats_svg(t):
    """A bare stat panel: one hero figure, three supporting ones, ink colors, no plot."""
    sans = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
    branches = " · ".join(t["branches"])
    tiles = [
        (40, "MERGED UPSTREAM", t["merged"], "into default branches", 64),
        (340, "BACKPORTS", t["backports"], branches or "release branches", 44),
        (600, "OPEN", t["open"], "in review upstream", 44),
        (830, "PROJECTS", t["projects"], "public upstreams", 44),
    ]
    body = ""
    for x, label, value, note, size in tiles:
        body += (
            f'<text x="{x}" y="46" class="label">{label}</text>'
            f'<text x="{x}" y="112" class="value" font-size="{size}">{value}</text>'
            f'<text x="{x}" y="140" class="note">{html.escape(note)}</text>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1040 168" width="1040" height="168" role="img" aria-label="{t['merged']} pull requests merged upstream, {t['backports']} backports, {t['open']} open, {t['projects']} projects">
<style>
text {{ font-family: {sans}; }}
.label {{ font-size: 13px; font-weight: 600; letter-spacing: 1.4px; fill: #8fb3c7; }}
.value {{ font-weight: 700; fill: #f4f9fc; }}
.note {{ font-size: 14px; fill: #a9c1cf; }}
</style>
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b171d"/><stop offset="1" stop-color="#16303c"/></linearGradient></defs>
<rect x="0.5" y="0.5" width="1039" height="167" rx="12" fill="url(#bg)" stroke="#2c5364"/>
<path d="M310 32V136M570 32V136M800 32V136" stroke="#2c5364"/>
{body}
</svg>
"""


def replace_block(readme, block):
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(readme):
        raise ValueError("README.md has no stats markers")
    return pattern.sub(lambda _: f"{START}\n{block}\n{END}", readme)


def main():
    authored = fetch_authored(ME)
    if not authored:
        raise RuntimeError("search returned no pull requests")
    summary = summarize(authored, fetch_candidates(authored), ME)
    readme_path = ROOT / "README.md"
    readme = replace_block(readme_path.read_text(), render_stats_block(summary, ME))
    svg = render_stats_svg(totals(summary))
    # Written only after every step above succeeded, so a failure keeps the last good numbers.
    readme_path.write_text(readme)
    (ROOT / "assets").mkdir(exist_ok=True)
    (ROOT / "assets" / "stats.svg").write_text(svg)
    print(json.dumps(totals(summary)))


if __name__ == "__main__":
    main()
