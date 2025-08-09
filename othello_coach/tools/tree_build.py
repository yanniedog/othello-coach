from __future__ import annotations
import argparse
import json
from typing import Dict, List, Tuple

from ..engine.bitboard import Position
from ..engine.search import Searcher, SearchConfig
from ..engine.eval import evaluate

# Simple tree builder (width-limited) with scoring goals. Exports JSON and DOT.

def legal_moves_list(pos: Position) -> List[int]:
    lm = pos.legal_mask()
    return [i for i in range(64) if (lm >> i) & 1]


def node_attrs(pos: Position) -> Dict:
    me, opp = pos.me_opp()
    # Minimal attributes for goals
    from ..engine.bitboard import legal_moves
    return {
        "score_side": evaluate(pos),
        "mob_self": bin(legal_moves(me, opp)).count("1"),
        "mob_opp": bin(legal_moves(opp, me)).count("1"),
        "corners_me": bin(me & 0x8100000000000081).count("1"),
        "corners_opp": bin(opp & 0x8100000000000081).count("1"),
    }


def goal_score(attrs: Dict, goal: str) -> float:
    if goal == "score_white":
        # Convert to White POV from side-to-move score
        # If stm==0 (Black), score_white = -score_side; else = score_side
        return attrs["score_white"] if "score_white" in attrs else attrs["score_side"]
    if goal == "min_opp_mob":
        return -attrs["mob_opp"]
    if goal == "score_side":
        return attrs["score_side"]
    return attrs["score_side"]


def build_tree(root: Position, depth:int, width:int, goal:str) -> Dict:
    eng = Searcher()
    cfg = SearchConfig(max_depth=min(4, depth))  # shallow for per-node attrs
    node_id = 0
    nodes = {}
    edges = []

    def rec(pos: Position, d:int) -> int:
        nonlocal node_id
        nid = node_id; node_id += 1
        attrs = node_attrs(pos)
        # derive white score from side score
        attrs["score_white"] = attrs["score_side"] if pos.stm==1 else -attrs["score_side"]
        nodes[nid] = {"hash": pos.hash64(), "stm": pos.stm, "attrs": attrs}
        if d == 0 or pos.terminal():
            return nid
        moves = legal_moves_list(pos)
        # score children by goal comparator
        scored = []
        for m in moves:
            child = pos.apply(m)
            # quick eval via search depth 1–2 for a proxy
            a = eng.search(child, cfg)
            ch_attrs = node_attrs(child)
            ch_attrs["score_white"] = ch_attrs["score_side"] if child.stm==1 else -ch_attrs["score_side"]
            s = goal_score(ch_attrs, goal)
            scored.append((s, m, child, ch_attrs, a.score))
        scored.sort(key=lambda x: x[0], reverse=True)
        for s, m, child, ch_attrs, raw in scored[:width]:
            cid = rec(child, d-1)
            edges.append({"from": nid, "to": cid, "move": m, "score": s})
        return nid

    root_id = rec(root, depth)
    return {"nodes": nodes, "edges": edges, "root": root_id}


def export_dot(tree: Dict, path: str):
    def label(nid:int) -> str:
        n = tree["nodes"][nid]
        s = n["attrs"]["score_side"]/100.0
        return f"{nid}\nscore={s:+.2f}"
    lines = ["digraph G {"]
    for nid in tree["nodes"].keys():
        lines.append(f"  {nid} [label=\"{label(nid)}\"];\n")
    for e in tree["edges"]:
        lines.append(f"  {e['from']} -> {e['to']} [label=\"{e['move']}\"];\n")
    lines.append("}")
    with open(path, "w") as f:
        f.write("".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", type=int, default=5)
    ap.add_argument("--width", type=int, default=6)
    ap.add_argument("--goal", type=str, default="score_white", choices=["score_white","score_side","min_opp_mob"])
    ap.add_argument("--out", type=str, default="tree.json")
    args = ap.parse_args()
    pos = Position.initial()
    tree = build_tree(pos, args.depth, args.width, args.goal)
    with open(args.out, "w") as f:
        json.dump(tree, f)
    export_dot(tree, args.out.replace(".json", ".dot"))
    print(f"Wrote {args.out} and DOT file")

if __name__ == "__main__":
    main()


