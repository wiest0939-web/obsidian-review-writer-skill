#!/usr/bin/env python3
"""Save a close-reading note into an Obsidian vault and ensure matrix scaffolding."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


SAFE_STATUS = {"close-read-complete", "skimmed", "not-eligible", "needs-review"}


def slugify(value: str) -> str:
    value = re.sub(r"[^\w\s.-]", "", value, flags=re.UNICODE)
    value = re.sub(r"\s+", "-", value.strip())
    return value[:120] or "untitled"


def yaml_escape(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].lstrip()
    return text.lstrip()


def build_frontmatter(args: argparse.Namespace) -> str:
    fields = {
        "citekey": args.citekey,
        "title": args.title,
        "authors": args.authors or "",
        "year": str(args.year) if args.year else "",
        "journal": args.journal or "",
        "doi": args.doi or "",
        "pmid": args.pmid or "",
        "disease": args.disease or "",
        "topic": args.topic or "",
        "study_type": args.study_type or "",
        "status": args.status,
        "source_file": str(Path(args.source_file).resolve()) if args.source_file else "",
    }
    lines = ["---"]
    for key, value in fields.items():
        if value:
            lines.append(f"{key}: {yaml_escape(value)}")
        else:
            lines.append(f"{key}:")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


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


def ensure_matrix(vault: Path) -> Path:
    matrix = vault / "02_evidence-matrix" / "evidence-matrix.md"
    if not matrix.exists():
        matrix.write_text(
            "# Evidence Matrix\n\n"
            "| Topic | Claim | Citekey | Source anchor | Evidence type | Strength | Review-ready sentence | Eligible |\n"
            "|---|---|---|---|---|---|---|---|\n",
            encoding="utf-8",
        )
    return matrix


def append_matrix_rows(matrix: Path, citekey: str, rows: list[str]) -> None:
    if not rows:
        return

    current = matrix.read_text(encoding="utf-8")
    additions = []
    for row in rows:
        fields = [part.strip() for part in row.split("|")]
        if len(fields) != 7:
            raise SystemExit(
                "--matrix-row must contain 7 pipe-separated fields: "
                "Topic|Claim|Source anchor|Evidence type|Strength|Review-ready sentence|Eligible"
            )
        topic, claim, anchor, evidence_type, strength, sentence, eligible = fields
        line = (
            f"| {markdown_cell(topic)} | {markdown_cell(claim)} | {markdown_cell(citekey)} | "
            f"{markdown_cell(anchor)} | {markdown_cell(evidence_type)} | {markdown_cell(strength)} | "
            f"{markdown_cell(sentence)} | {markdown_cell(eligible)} |"
        )
        if line not in current:
            additions.append(line)

    if additions:
        matrix.write_text(current.rstrip() + "\n" + "\n".join(additions) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Save a close-reading note into an Obsidian vault."
    )
    parser.add_argument("--vault", required=True, help="Path to the Obsidian vault.")
    parser.add_argument("--citekey", required=True, help="Stable citation key.")
    parser.add_argument("--title", required=True, help="Paper title.")
    parser.add_argument("--authors", default="", help="Author string, such as 'Zhang et al.'.")
    parser.add_argument("--year", type=int, help="Publication year.")
    parser.add_argument("--journal", default="", help="Journal name.")
    parser.add_argument("--doi", default="", help="DOI.")
    parser.add_argument("--pmid", default="", help="PMID.")
    parser.add_argument("--disease", default="", help="Disease or condition.")
    parser.add_argument("--topic", default="", help="Review topic.")
    parser.add_argument("--study-type", default="", help="Study type.")
    parser.add_argument(
        "--status",
        default="close-read-complete",
        choices=sorted(SAFE_STATUS),
        help="Reading eligibility status.",
    )
    parser.add_argument("--source-file", default="", help="Original PDF/full-text path.")
    parser.add_argument(
        "--note-file",
        required=True,
        help="Markdown file containing the note body, with or without frontmatter.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing note with the same citekey.",
    )
    parser.add_argument(
        "--matrix-row",
        action="append",
        default=[],
        help=(
            "Append an evidence matrix row as "
            "'Topic|Claim|Source anchor|Evidence type|Strength|Review-ready sentence|Eligible'. "
            "May be passed multiple times."
        ),
    )
    args = parser.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    note_file = Path(args.note_file).expanduser().resolve()

    if not note_file.exists():
        raise SystemExit(f"Note file does not exist: {note_file}")

    ensure_vault(vault)
    matrix = ensure_matrix(vault)

    body = strip_frontmatter(note_file.read_text(encoding="utf-8"))
    filename = f"{slugify(args.citekey)} - {slugify(args.title)}.md"
    output = vault / "01_reading-notes" / filename

    if output.exists() and not args.overwrite:
        raise SystemExit(f"Refusing to overwrite existing note: {output}")

    output.write_text(build_frontmatter(args) + body, encoding="utf-8")
    append_matrix_rows(matrix, args.citekey, args.matrix_row)

    index = vault / "01_reading-notes" / "index.md"
    link = f"[[{output.stem}]]"
    entry = f"- {link} ({args.year or 'n.d.'}) - {args.status}\n"
    if index.exists():
        current = index.read_text(encoding="utf-8")
        if link not in current:
            index.write_text(current.rstrip() + "\n" + entry, encoding="utf-8")
    else:
        index.write_text("# Reading Notes Index\n\n" + entry, encoding="utf-8")

    print(f"saved_note={output}")
    print(f"evidence_matrix={matrix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
