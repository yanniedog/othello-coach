from __future__ import annotations

import json
from typing import Dict


def to_json(tree: Dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tree, f)


def to_dot(tree: Dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("digraph G {\n")
        for h, n in tree["nodes"].items():
            f.write(f'  "{h}" [label="{n["score"]}"];\n')
        for e in tree["edges"]:
            f.write(f'  "{e["from"]}" -> "{e["to"]}" [label="{e["move"]}"];\n')
        f.write("}\n")
