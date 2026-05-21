#!/usr/bin/env python3
"""Manage a batch reading queue for Obsidian review projects."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


FIELDS = [
    "id",
    "status",
    "title",
    "citekey",
    "source_file",
    "note_path",
    "created_at",
    "started_at",
    "completed_at",
    "error",
]

VALID_STATUSES = {"pending", "in-progress", "complete", "needs-review", "excluded", "error"}
TERMINAL_STATUSES = {"complete", "needs-review", "excluded", "error"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_vault(vault: Path) -> None:
    for folder in [
        "00_search-strategy",
        "01_reading-notes",
        "02_evidence-matrix",
        "03_topic-cards",
        "04_outline",
        "05_drafts",
        "06_claim-audit",
    ]:
        (vault / folder).mkdir(parents=True, exist_ok=True)


def queue_csv(vault: Path) -> Path:
    return vault / "00_search-strategy" / "reading-queue.csv"


def queue_md(vault: Path) -> Path:
    return vault / "00_search-strategy" / "reading-queue.md"


def load_rows(vault: Path) -> list[dict[str, str]]:
    path = queue_csv(vault)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(vault: Path, rows: list[dict[str, str]]) -> None:
    path = queue_csv(vault)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})
    write_markdown(vault, rows)


def markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def obsidian_link(vault: Path, path_value: str) -> str:
    if not path_value:
        return ""
    path = Path(path_value)
    try:
        rel = path.resolve().relative_to(vault.resolve())
        if rel.suffix.lower() == ".md":
            return f"[[{rel.with_suffix('').as_posix()}]]"
    except ValueError:
        pass
    return path_value


def write_markdown(vault: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row.get("status", "") for row in rows)
    lines = [
        "# Reading Queue",
        "",
        "## Status",
        "",
    ]
    for status in ["pending", "in-progress", "complete", "needs-review", "excluded", "error"]:
        lines.append(f"- {status}: {counts.get(status, 0)}")
    lines.extend(
        [
            "",
            "## Queue",
            "",
            "| ID | Status | Title | Citekey | Source file | Note | Error |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_cell(row.get("id", "")),
                    markdown_cell(row.get("status", "")),
                    markdown_cell(row.get("title", "")),
                    markdown_cell(row.get("citekey", "")),
                    markdown_cell(row.get("source_file", "")),
                    markdown_cell(obsidian_link(vault, row.get("note_path", ""))),
                    markdown_cell(row.get("error", "")),
                ]
            )
            + " |"
        )
    queue_md(vault).write_text("\n".join(lines) + "\n", encoding="utf-8")


def title_from_pdf(path: Path) -> str:
    title = re.sub(r"[_-]+", " ", path.stem)
    title = re.sub(r"\s+", " ", title).strip()
    return title or path.stem


def row_id(path: Path) -> str:
    normalized = str(path.resolve()).lower()
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]


def discover_pdfs(pdf_dir: Path, recursive: bool) -> list[Path]:
    pattern = "**/*.pdf" if recursive else "*.pdf"
    return sorted(pdf_dir.glob(pattern), key=lambda item: str(item).lower())


def cmd_init(args: argparse.Namespace) -> int:
    vault = Path(args.vault).expanduser().resolve()
    pdf_dir = Path(args.pdf_dir).expanduser().resolve()
    if not pdf_dir.exists():
        raise SystemExit(f"PDF directory does not exist: {pdf_dir}")
    ensure_vault(vault)

    rows = load_rows(vault)
    known_paths = {str(Path(row.get("source_file", "")).resolve()).lower() for row in rows if row.get("source_file")}
    created = now_iso()
    added = 0
    for pdf in discover_pdfs(pdf_dir, args.recursive):
        resolved = str(pdf.resolve())
        if resolved.lower() in known_paths:
            continue
        rows.append(
            {
                "id": row_id(pdf),
                "status": "pending",
                "title": title_from_pdf(pdf),
                "citekey": "",
                "source_file": resolved,
                "note_path": "",
                "created_at": created,
                "started_at": "",
                "completed_at": "",
                "error": "",
            }
        )
        added += 1

    write_rows(vault, rows)
    print(f"queue_csv={queue_csv(vault)}")
    print(f"queue_md={queue_md(vault)}")
    print(f"added={added}")
    print(f"total={len(rows)}")
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    vault = Path(args.vault).expanduser().resolve()
    rows = load_rows(vault)
    for row in rows:
        if row.get("status") == "pending":
            row["status"] = "in-progress"
            row["started_at"] = row.get("started_at") or now_iso()
            row["error"] = ""
            write_rows(vault, rows)
            print(f"id={row.get('id', '')}")
            print(f"title={row.get('title', '')}")
            print(f"source_file={row.get('source_file', '')}")
            return 0
    print("next=")
    print("message=no pending items")
    return 0


def cmd_mark(args: argparse.Namespace) -> int:
    if args.status not in VALID_STATUSES:
        raise SystemExit(f"Invalid status: {args.status}")

    vault = Path(args.vault).expanduser().resolve()
    rows = load_rows(vault)
    target = None
    for row in rows:
        if row.get("id") == args.id:
            target = row
            break
    if target is None:
        raise SystemExit(f"Queue id not found: {args.id}")

    target["status"] = args.status
    if args.title:
        target["title"] = args.title
    if args.citekey:
        target["citekey"] = args.citekey
    if args.note_path:
        target["note_path"] = str(Path(args.note_path).expanduser().resolve())
    if args.error:
        target["error"] = args.error
    elif args.status != "error":
        target["error"] = ""
    if args.status == "in-progress":
        target["started_at"] = target.get("started_at") or now_iso()
    if args.status in TERMINAL_STATUSES:
        target["completed_at"] = now_iso()

    write_rows(vault, rows)
    print(f"updated={args.id}")
    print(f"status={args.status}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    vault = Path(args.vault).expanduser().resolve()
    rows = load_rows(vault)
    counts = Counter(row.get("status", "") for row in rows)
    print(f"total={len(rows)}")
    for status in ["pending", "in-progress", "complete", "needs-review", "excluded", "error"]:
        print(f"{status}={counts.get(status, 0)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage an Obsidian batch reading queue.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create or extend a queue from a PDF folder.")
    init.add_argument("--vault", required=True, help="Path to the Obsidian vault.")
    init.add_argument("--pdf-dir", required=True, help="Folder containing PDF files.")
    init.add_argument("--recursive", action="store_true", help="Scan PDF folder recursively.")
    init.set_defaults(func=cmd_init)

    next_item = subparsers.add_parser("next", help="Claim the next pending PDF.")
    next_item.add_argument("--vault", required=True, help="Path to the Obsidian vault.")
    next_item.set_defaults(func=cmd_next)

    mark = subparsers.add_parser("mark", help="Update one queue item.")
    mark.add_argument("--vault", required=True, help="Path to the Obsidian vault.")
    mark.add_argument("--id", required=True, help="Queue item id.")
    mark.add_argument("--status", required=True, choices=sorted(VALID_STATUSES), help="New status.")
    mark.add_argument("--citekey", default="", help="Citation key after metadata extraction.")
    mark.add_argument("--title", default="", help="Corrected title after metadata extraction.")
    mark.add_argument("--note-path", default="", help="Saved Obsidian note path.")
    mark.add_argument("--error", default="", help="Error or review reason.")
    mark.set_defaults(func=cmd_mark)

    stats = subparsers.add_parser("stats", help="Print queue counts.")
    stats.add_argument("--vault", required=True, help="Path to the Obsidian vault.")
    stats.set_defaults(func=cmd_stats)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
