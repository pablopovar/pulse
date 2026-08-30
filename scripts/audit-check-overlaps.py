#!/usr/bin/env python3
from __future__ import annotations
import ast, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "audit-app" / "audits" / "geo_aeo" / "engine.py"
sys.path.insert(0, str(ROOT / "audit-app"))
from reports.prioritization import canonical_check_title, overlap_candidates

def extract_titles(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    titles = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "add" and len(node.args) >= 4:
            title = node.args[3]
            if isinstance(title, ast.Constant) and isinstance(title.value, str):
                titles.append(title.value)
    return sorted(set(titles))

def main() -> int:
    titles = extract_titles(ENGINE)
    rows = overlap_candidates(titles)
    print("# Check overlap audit\n")
    print(f"Checks inspected: {len(titles)}")
    print(f"Potential overlap pairs: {len(rows)}\n")
    print("| Check A | Check B | Similarity | Explicit report alias |")
    print("|---|---|---:|---|")
    for row in rows:
        print(f"| {row['a']} | {row['b']} | {row['similarity']:.3f} | {'yes' if row['explicit_alias'] else 'review'} |")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
