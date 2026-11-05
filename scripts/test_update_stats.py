"""Metric rules for update_stats, written from the agreed definition."""
import pytest

import update_stats as us

ME = "me"
ZEPHYR = "zephyrproject-rtos/zephyr"
LVGL = "lvgl/lvgl"


def pr(number, base="main", state="MERGED", repo=ZEPHYR, title="fix", logins=()):
    return {
        "repo": repo,
        "number": number,
        "title": title,
        "url": f"https://github.com/{repo}/pull/{number}",
        "state": state,
        "base": base,
        "default": "master" if repo == LVGL else "main",
        "logins": list(logins),
    }


def zephyr_stats(authored, candidates):
    return us.summarize(authored, candidates, ME)[ZEPHYR]


def test_merged_counts_only_the_default_branch():
    stats = zephyr_stats([pr(1), pr(2), pr(3, base="v3.7-branch")], [])
    assert stats["merged"] == 2


def test_own_backport_is_a_backport_and_not_also_merged():
    stats = zephyr_stats([pr(1), pr(2, base="v4.4-branch")], [])
    assert (stats["merged"], len(stats["backports"])) == (1, 1)


def test_backport_opened_by_someone_else_counts_when_it_carries_my_commit():
    candidate = pr(9, base="v4.3-branch", logins=[ME])
    assert len(zephyr_stats([pr(1)], [candidate])["backports"]) == 1


def test_backport_without_my_commit_does_not_count():
    candidate = pr(9, base="v4.3-branch", logins=["someone"])
    assert zephyr_stats([pr(1)], [candidate])["backports"] == []


def test_cross_reference_to_the_default_branch_is_not_a_backport():
    candidate = pr(9, base="main", logins=[ME])
    assert zephyr_stats([pr(1)], [candidate])["backports"] == []


def test_backport_seen_twice_counts_once():
    own = pr(2, base="v4.4-branch", logins=[ME])
    twice = pr(9, base="v4.4-branch", logins=[ME])
    stats = zephyr_stats([pr(1), own], [own, twice, twice])
    assert sorted(b["number"] for b in stats["backports"]) == [2, 9]


def test_my_backport_of_a_fix_by_someone_else_counts():
    assert len(zephyr_stats([pr(1), pr(2, base="v3.7-branch", logins=["other"])], [])["backports"]) == 1


def test_open_includes_open_backports_and_merged_excludes_them():
    candidate = pr(9, base="v4.5-branch", state="OPEN", logins=[ME])
    stats = zephyr_stats([pr(1), pr(2, state="OPEN")], [candidate])
    assert stats["open"] == 2
    assert stats["merged"] == 1
    assert [b["number"] for b in stats["merged_backports"]] == []


def test_closed_pull_requests_count_nowhere():
    stats = zephyr_stats([pr(1, state="CLOSED"), pr(2, state="CLOSED", base="v4.4-branch")], [])
    assert (stats["merged"], stats["open"], stats["merged_backports"]) == (0, 0, [])


def test_default_branch_is_per_repository():
    stats = us.summarize([pr(1, base="master", repo=LVGL)], [], ME)[LVGL]
    assert (stats["merged"], stats["backports"]) == (1, [])


def test_totals_add_up_across_repositories():
    summary = us.summarize(
        [pr(1), pr(2, base="v3.7-branch"), pr(3, state="OPEN"), pr(4, base="master", repo=LVGL)],
        [],
        ME,
    )
    assert us.totals(summary) == {
        "merged": 2,
        "backports": 1,
        "open": 1,
        "projects": 2,
        "branches": ["v3.7 LTS"],
    }


def test_branches_list_only_merged_backports_in_version_order():
    summary = us.summarize(
        [
            pr(1, base="v4.4-branch"),
            pr(2, base="v3.7-branch"),
            pr(3, base="v4.10-branch"),
            pr(4, base="v4.5-branch", state="OPEN"),
        ],
        [],
        ME,
    )
    assert us.totals(summary)["branches"] == ["v3.7 LTS", "v4.4", "v4.10"]


def test_table_shows_every_project_and_keeps_focus_text():
    summary = us.summarize([pr(1), pr(2, repo="new/project", base="trunk")], [], ME)
    table = us.render_stats_block(summary, ME)
    assert "Zephyr" in table
    assert "[new/project](https://github.com/new/project)" in table


def test_backport_list_groups_branches_under_one_fix():
    summary = us.summarize(
        [
            pr(1, base="v4.4-branch", title="[backport v4.4-branch] net: fix it"),
            pr(2, base="v3.7-branch", title="[Backport v3.7-branch] net: fix it"),
        ],
        [],
        ME,
    )
    block = us.render_stats_block(summary, ME)
    assert block.count("net: fix it") == 1
    assert block.index("v3.7") < block.index("v4.4")


def test_titles_are_html_escaped():
    summary = us.summarize([pr(1, base="v4.4-branch", title="a <b> & c")], [], ME)
    assert "a &lt;b&gt; &amp; c" in us.render_stats_block(summary, ME)


def test_stats_svg_is_well_formed_and_shows_the_totals():
    import xml.etree.ElementTree as ET

    totals = {"merged": 60, "backports": 17, "open": 62, "projects": 9, "branches": ["v3.7 LTS", "v4.3"]}
    svg = us.render_stats_svg(totals)
    ET.fromstring(svg)
    for text in (">60<", ">17<", ">62<", ">9<", "v3.7 LTS"):
        assert text in svg


def test_replace_block_keeps_the_text_around_the_markers():
    readme = f"before\n{us.START}\nold\n{us.END}\nafter\n"
    assert us.replace_block(readme, "new") == f"before\n{us.START}\nnew\n{us.END}\nafter\n"


def test_replace_block_refuses_a_readme_without_markers():
    with pytest.raises(ValueError):
        us.replace_block("no markers", "new")


def test_search_at_the_result_cap_fails_instead_of_undercounting():
    with pytest.raises(RuntimeError):
        us.check_search_cap(1000)
