"""Knowledge (OKF) command line.

    python -m app.knowledge generate   rebuild storage/knowledge/ from PostgreSQL
    python -m app.knowledge validate   compare with the dataset's 1,202 edges and 297 OKF items
"""

import argparse
import sys

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.knowledge.graph import all_edges
from app.knowledge.okf import build_items, write_items
from app.knowledge.validate import compare_edges, compare_items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.knowledge")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("generate", help="rebuild the OKF folder from PostgreSQL")
    commands.add_parser("validate", help="compare with the dataset's knowledge files")
    args = parser.parse_args(argv)
    settings = get_settings()

    with SessionLocal() as db:
        if args.command == "generate":
            result = write_items(db, settings.storage_dir / "knowledge")
            print(f"Wrote {result['items']} OKF items and {result['edges']} edges to {result['folder']}")
            return 0
        edges = all_edges(db)
        edge_report = compare_edges(edges, settings.data_dir / "structured" / "relationships.json")
        item_report = compare_items(build_items(db, edges), settings.data_dir / "knowledge" / "OKF_style" / "index.json")
    print(f"Edges: {edge_report['generated']} generated vs {edge_report['fixture']} in the dataset | "
          f"missing {len(edge_report['missing'])} | extra {len(edge_report['extra'])} | "
          f"source_type mismatches {len(edge_report['source_type_mismatches'])}")
    print(f"  citation differences (same edge and trust level): {edge_report['citation_differences'] or 'none'}")
    print(f"Items: {item_report['generated']} generated vs {item_report['fixture']} in the dataset | "
          f"missing {len(item_report['missing'])} | extra {len(item_report['extra'])}")
    ok = not (edge_report["missing"] or edge_report["extra"] or edge_report["source_type_mismatches"]
              or item_report["missing"] or item_report["extra"])
    print("VALID" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
