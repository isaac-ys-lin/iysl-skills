#!/usr/bin/env python3
"""Render the ask-matt flow map as one self-contained HTML page.

Without an answer file the page is the full map. With one, the recommended
route is highlighted and the ruled-out neighbours are listed beside it.

    render_flow_map.py --check
    render_flow_map.py --out map.html
    render_flow_map.py --answer answer.json --out map.html
"""

from __future__ import annotations

import argparse
import json
import sys
from html import escape
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP = SKILL_ROOT / "assets" / "flow-map.json"

KIND_LABELS = {
    "flow": "主線",
    "detour": "繞道",
    "bridge": "橋接",
    "internal": "被內部驅動",
    "onramp": "入口",
    "reference": "詞彙",
    "standalone": "獨立",
    "precondition": "前置",
}
INVOCATION_LABELS = {"user": "只有你能叫", "model": "agent 也會自己叫"}


class MapError(ValueError):
    """The map or the answer file does not satisfy the structural contract."""


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:  # pragma: no cover - argparse guards most cases
        raise MapError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise MapError(f"invalid JSON in {path}: {exc}") from exc


def check_map(data: dict, skill_root: Path = SKILL_ROOT) -> dict:
    """Validate the map and return {node_id: node}. Raises MapError."""
    for key in ("version", "title", "lanes", "nodes", "steps", "branches", "edges", "phase_boundary"):
        if key not in data:
            raise MapError(f"map is missing required key: {key}")

    lanes = {lane["id"] for lane in data["lanes"]}
    if len(lanes) != len(data["lanes"]):
        raise MapError("duplicate lane id")

    nodes: dict[str, dict] = {}
    for node in data["nodes"]:
        node_id = node["id"]
        if node_id in nodes:
            raise MapError(f"duplicate node id: {node_id}")
        if node["lane"] not in lanes:
            raise MapError(f"{node_id}: unknown lane {node['lane']}")
        if node["kind"] not in KIND_LABELS:
            raise MapError(f"{node_id}: unknown kind {node['kind']}")
        if node["invocation"] not in INVOCATION_LABELS:
            raise MapError(f"{node_id}: unknown invocation {node['invocation']}")
        for field in ("label", "one_line", "when"):
            if not str(node.get(field, "")).strip():
                raise MapError(f"{node_id}: empty {field}")
        nodes[node_id] = node

    def require_node(node_id: str, where: str) -> None:
        if node_id not in nodes:
            raise MapError(f"{where}: unknown node {node_id}")

    for node in data["nodes"]:
        for target in node.get("drives", []):
            require_node(target, f"{node['id']}.drives")
        if "merges_into" in node:
            require_node(node["merges_into"], f"{node['id']}.merges_into")

    branches = {branch["id"]: branch for branch in data["branches"]}
    if len(branches) != len(data["branches"]):
        raise MapError("duplicate branch id")
    for branch in data["branches"]:
        if not branch["options"]:
            raise MapError(f"{branch['id']}: no options")
        for option in branch["options"]:
            for target in option["targets"]:
                require_node(target, f"{branch['id']}.targets")

    for step in data["steps"]:
        if ("node" in step) == ("branch" in step):
            raise MapError(f"step {step.get('n')}: needs exactly one of node/branch")
        if "node" in step:
            require_node(step["node"], "steps")
        elif step["branch"] not in branches:
            raise MapError(f"steps: unknown branch {step['branch']}")

    for edge in data["edges"]:
        require_node(edge["from"], "edges")
        require_node(edge["to"], "edges")

    reference = data["phase_boundary"].get("reference")
    if reference and not (skill_root / reference).exists():
        raise MapError(f"phase_boundary.reference does not exist: {reference}")
    if not data["phase_boundary"].get("options"):
        raise MapError("phase_boundary: no options")

    return nodes


def check_answer(answer: dict, nodes: dict[str, dict]) -> None:
    if not str(answer.get("situation", "")).strip():
        raise MapError("answer: empty situation")
    if not answer.get("route"):
        raise MapError("answer: route is empty")
    for group in ("route", "excluded"):
        for item in answer.get(group, []):
            if item["node"] not in nodes:
                raise MapError(f"answer.{group}: unknown node {item['node']}")
            if not str(item.get("why", "")).strip():
                raise MapError(f"answer.{group}.{item['node']}: empty why")


def node_card(node: dict, route_order: dict[str, int]) -> str:
    order = route_order.get(node["id"])
    classes = "card" + (" on-route" if order else "")
    badge = f'<span class="order">{order}</span>' if order else ""
    rows = [f'<p class="one-line">{escape(node["one_line"])}</p>']
    rows.append(f'<p class="when"><b>什麼時候用</b>：{escape(node["when"])}</p>')
    if node.get("not_when"):
        rows.append(f'<p class="not-when"><b>什麼時候不用</b>：{escape(node["not_when"])}</p>')
    if node.get("note"):
        rows.append(f'<p class="note">{escape(node["note"])}</p>')
    return (
        f'<article class="{classes}" id="node-{escape(node["id"])}">'
        f'<header>{badge}<h3>{escape(node["label"])}</h3>'
        f'<span class="tag kind-{escape(node["kind"])}">{KIND_LABELS[node["kind"]]}</span>'
        f'<span class="tag invocation">{INVOCATION_LABELS[node["invocation"]]}</span>'
        f"</header>{''.join(rows)}</article>"
    )


def branch_card(branch: dict, nodes: dict[str, dict], route_order: dict[str, int]) -> str:
    options = []
    for option in branch["options"]:
        chips = "".join(
            f'<a class="chip{" on-route" if target in route_order else ""}" href="#node-{escape(target)}">'
            f"{escape(nodes[target]['label'])}</a>"
            for target in option["targets"]
        )
        options.append(
            f'<li><b>{escape(option["label"])}</b>'
            f'<p>{escape(option["why"])}</p>'
            f'<div class="chips">{chips}</div></li>'
        )
    return (
        f'<article class="card branch" id="branch-{escape(branch["id"])}">'
        f'<header><h3>{escape(branch["question"])}</h3></header>'
        f'<ul class="options">{"".join(options)}</ul></article>'
    )


def render_route(answer: dict, nodes: dict[str, dict]) -> str:
    steps = "".join(
        f'<li><a href="#node-{escape(item["node"])}">{escape(nodes[item["node"]]["label"])}</a>'
        f'<p>{escape(item["why"])}</p></li>'
        for item in answer["route"]
    )
    excluded = "".join(
        f'<li><b>{escape(nodes[item["node"]]["label"])}</b>：{escape(item["why"])}</li>'
        for item in answer.get("excluded", [])
    )
    excluded_block = f'<div class="excluded"><h3>排除掉的鄰居</h3><ul>{excluded}</ul></div>' if excluded else ""
    notes = "".join(f"<li>{escape(note)}</li>" for note in answer.get("notes", []))
    notes_block = f'<div class="notes"><h3>提醒</h3><ul>{notes}</ul></div>' if notes else ""
    return (
        '<section class="route-panel">'
        f'<p class="eyebrow">你的情境</p><p class="situation">{escape(answer["situation"])}</p>'
        f'<h2>建議路線</h2><ol class="route">{steps}</ol>'
        f"{excluded_block}{notes_block}</section>"
    )


def render(data: dict, nodes: dict[str, dict], answer: dict | None) -> str:
    route_order = {}
    if answer:
        for index, item in enumerate(answer["route"], start=1):
            route_order.setdefault(item["node"], index)

    branches = {branch["id"]: branch for branch in data["branches"]}
    lanes = {lane["id"]: lane for lane in data["lanes"]}

    main_steps = []
    for step in data["steps"]:
        body = (
            node_card(nodes[step["node"]], route_order)
            if "node" in step
            else branch_card(branches[step["branch"]], nodes, route_order)
        )
        main_steps.append(
            f'<li class="step"><div class="step-head"><span class="n">{escape(str(step["n"]))}</span>'
            f'<h3>{escape(step["headline"])}</h3></div>{body}</li>'
        )

    main_nodes = [
        node
        for node in data["nodes"]
        if node["lane"] == "main" and node["id"] not in {s.get("node") for s in data["steps"]}
    ]
    main_rest = "".join(node_card(node, route_order) for node in main_nodes)

    sections = [
        '<section class="lane" id="lane-main">'
        f'<header><h2>{escape(lanes["main"]["label"])}</h2>'
        f'<p>{escape(lanes["main"]["blurb"])}</p></header>'
        f'<ol class="steps">{"".join(main_steps)}</ol>'
        f'<div class="grid">{main_rest}</div>'
        f'<div class="hygiene"><h3>Context 衛生</h3>'
        f'<p>{escape(data["context_hygiene"]["rule"])}</p>'
        f'<p>{escape(data["context_hygiene"]["limit"])}</p></div>'
        "</section>"
    ]
    for lane_id, lane in lanes.items():
        if lane_id == "main":
            continue
        cards = "".join(
            node_card(node, route_order) for node in data["nodes"] if node["lane"] == lane_id
        )
        sections.append(
            f'<section class="lane" id="lane-{escape(lane_id)}">'
            f'<header><h2>{escape(lane["label"])}</h2><p>{escape(lane["blurb"])}</p></header>'
            f'<div class="grid">{cards}</div></section>'
        )

    boundary_rows = "".join(
        f'<tr><th>{escape(option["option"])}</th><td>{escape(option["does"])}</td>'
        f'<td>{escape(option["pick_when"])}</td></tr>'
        for option in data["phase_boundary"]["options"]
    )
    sections.append(
        '<section class="lane" id="lane-phase">'
        "<header><h2>Phase 邊界</h2>"
        f'<p>{escape(data["phase_boundary"]["rule"])}</p></header>'
        '<div class="table-wrap"><table><thead><tr><th>選項</th><th>做什麼</th>'
        f"<th>什麼時候選</th></tr></thead><tbody>{boundary_rows}</tbody></table></div>"
        f'<p class="note">完整的判斷樹在 <code>{escape(data["phase_boundary"]["reference"])}</code>。</p>'
        "</section>"
    )

    return TEMPLATE.format(
        title=escape(data["title"]),
        subtitle=escape(data["subtitle"]),
        route_panel=render_route(answer, nodes) if answer else "",
        sections="".join(sections),
    )


TEMPLATE = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ color-scheme: light; --ink:#192126; --muted:#657078; --paper:#fbfaf6; --card:#fff; --line:#d8d9d5; --accent:#086f68; --warm:#a3452e; --route:#0b5f9e; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; color:var(--ink); background:var(--paper); line-height:1.65; font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC",sans-serif; }}
.page {{ width:min(1080px,calc(100% - 32px)); margin-inline:auto; padding-bottom:72px; }}
header.hero {{ padding:44px 0 26px; border-bottom:2px solid var(--accent); }}
.eyebrow {{ color:var(--warm); font-size:.78rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; margin:0; }}
h1 {{ margin:.2rem 0 .4rem; font-family:ui-serif,Georgia,"Noto Serif TC",serif; font-size:clamp(1.9rem,4vw,3rem); line-height:1.1; }}
h2 {{ margin:0; font-size:clamp(1.3rem,2.6vw,1.8rem); }}
h3 {{ margin:0; font-size:1.05rem; }}
p {{ margin:.4rem 0; }}
a {{ color:var(--accent); text-underline-offset:3px; }}
.lane {{ margin-top:46px; }}
.lane > header {{ border-bottom:1px solid var(--line); padding-bottom:10px; margin-bottom:18px; }}
.lane > header p {{ color:var(--muted); }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:14px; }}
.card {{ border:1px solid var(--line); border-radius:12px; background:var(--card); padding:16px 18px; }}
.card > header {{ display:flex; flex-wrap:wrap; align-items:center; gap:8px; margin-bottom:6px; }}
.card h3 {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
.tag {{ border:1px solid var(--line); border-radius:999px; padding:2px 9px; font-size:.74rem; color:var(--muted); }}
.tag.kind-flow, .tag.kind-onramp {{ border-color:#bad4d1; background:#f0f8f7; color:#0d5d57; }}
.tag.kind-detour, .tag.kind-bridge {{ border-color:#e3c9a8; background:#fdf6ec; color:#8a5a1c; }}
.one-line {{ font-size:1rem; }}
.when, .not-when, .note {{ font-size:.9rem; color:#45535b; }}
.not-when {{ color:var(--warm); }}
.note {{ border-left:3px solid var(--line); padding-left:10px; }}
.steps {{ list-style:none; margin:0 0 18px; padding:0; display:grid; gap:14px; }}
.step-head {{ display:flex; align-items:center; gap:10px; margin-bottom:8px; }}
.step-head .n {{ display:grid; place-items:center; width:26px; height:26px; flex:none; border-radius:50%; background:var(--accent); color:#fff; font-size:.84rem; font-weight:800; }}
.step:not(:last-child)::after {{ content:"↓"; display:block; text-align:center; color:var(--accent); font-size:1.2rem; font-weight:900; margin-top:8px; }}
.branch .options {{ list-style:none; margin:8px 0 0; padding:0; display:grid; gap:10px; }}
.branch .options > li {{ border-left:3px solid var(--accent); padding-left:12px; }}
.branch .options p {{ font-size:.9rem; color:#45535b; }}
.chips {{ display:flex; flex-wrap:wrap; gap:6px; }}
.chip {{ border:1px solid var(--line); border-radius:999px; padding:3px 10px; font-size:.8rem; text-decoration:none; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
.chip.on-route, .card.on-route {{ border-color:var(--route); box-shadow:0 0 0 2px #0b5f9e22; }}
.card.on-route {{ background:#f4f9fd; }}
.order {{ display:grid; place-items:center; width:24px; height:24px; flex:none; border-radius:50%; background:var(--route); color:#fff; font-size:.8rem; font-weight:800; }}
.route-panel {{ margin-top:26px; border:2px solid var(--route); border-radius:14px; background:#f4f9fd; padding:20px 22px; }}
.situation {{ font-size:1.05rem; }}
.route {{ margin:.5rem 0 0; padding-left:1.3rem; }}
.route li {{ margin-bottom:8px; }}
.route a {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-weight:700; }}
.route p, .excluded li, .notes li {{ font-size:.92rem; color:#37454d; margin:.15rem 0; }}
.excluded, .notes {{ margin-top:14px; }}
.hygiene {{ margin-top:18px; border:1px dashed var(--warm); border-radius:12px; padding:14px 18px; background:#fdf6ec; }}
.hygiene p {{ font-size:.92rem; }}
.table-wrap {{ overflow-x:auto; }}
table {{ width:100%; min-width:620px; border-collapse:collapse; }}
th, td {{ border-bottom:1px solid var(--line); padding:10px; text-align:left; vertical-align:top; font-size:.92rem; }}
thead th {{ background:#f2f2ee; color:#435159; }}
tbody th {{ white-space:nowrap; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
</style>
</head>
<body>
<div class="page">
<header class="hero">
<p class="eyebrow">ask-matt</p>
<h1>{title}</h1>
<p>{subtitle}</p>
</header>
{route_panel}
{sections}
</div>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--answer", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--check", action="store_true", help="validate only, render nothing")
    args = parser.parse_args(argv)

    try:
        data = load_json(args.map)
        nodes = check_map(data, args.map.resolve().parents[1])
        answer = None
        if args.answer:
            answer = load_json(args.answer)
            check_answer(answer, nodes)
    except MapError as exc:
        print(f"check failed: {exc}", file=sys.stderr)
        return 1

    if args.check:
        scope = "map" if answer is None else "map and answer"
        print(f"check passed: {scope} ({len(nodes)} nodes)")
        return 0

    if args.out is None:
        print("--out is required unless --check is used", file=sys.stderr)
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(data, nodes, answer), encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
