---
name: obsidian-review-writer
description: Evidence-first literature review workflow for Codex using Obsidian as the auditable reading-note, unattended batch reading queue, and evidence-matrix store. Use when the user wants to write a scholarly review, reduce AI hallucinations, force full-text reading before writing, batch-process PDFs one by one without per-paper confirmation, create structured close-reading notes from PDFs, store notes in an Obsidian vault, build an evidence matrix, draft review sections only from validated notes, or audit citations and claims against read literature.
---

# Obsidian Review Writer

## Core Rule

Do not draft review prose from memory, abstracts, or general knowledge. Build a traceable evidence chain:

`PDF full text -> close-reading note in Obsidian -> evidence matrix -> section outline -> draft -> claim audit`.

Only cite literature that has a completed Obsidian close-reading note with source anchors. A source anchor is a page number, figure, table, section heading, quote fragment, or other location that lets the user verify the claim in the full text.

## Workflow

1. Confirm the Obsidian vault path and project folder. If not provided, infer from the current workspace or ask one concise question.
2. Create or use this vault structure:

```text
00_search-strategy/
01_reading-notes/
02_evidence-matrix/
03_topic-cards/
04_outline/
05_drafts/
06_claim-audit/
```

3. If the user provides a PDF folder or multiple source files, initialize a reading queue with `scripts/manage_reading_queue.py`.
4. Process the queue one item at a time: claim the next pending PDF, read the full text, generate a close-reading note, save it to Obsidian, then mark the queue item complete or needing review.
5. Update an evidence matrix in `02_evidence-matrix/evidence-matrix.md`.
6. Continue automatically to the next pending queue item until the requested limit is reached, the queue is exhausted, or a hard blocker prevents all further work.
7. Draft outlines and prose only from completed notes and matrix rows.
8. After each drafted section, create a claim audit table in `06_claim-audit/` mapping every substantive claim to supporting citekeys and source anchors.

## Unattended Batch Mode

If the user says they do not need confirmation during reading, run in unattended batch mode.

In unattended mode:

- Do not ask for confirmation after each paper.
- Do not pause for subjective decisions such as whether a paper is useful; classify it using the queue status rules.
- If a paper cannot be read reliably, mark it `needs-review` or `error`, record the reason, and continue to the next pending item.
- If metadata is incomplete but the full text is readable, create the note with available metadata, mark uncertain fields clearly, and use `needs-review` only when the missing metadata affects citation reliability.
- Continue until the requested batch size is complete, the queue has no pending items, or a hard blocker affects the whole batch.
- If the user asks to read all papers, process until the queue has no `pending` items; do not impose an arbitrary batch-size stop.
- At the end, report counts by status, saved note paths, evidence rows added, and items requiring review.

Only interrupt the user mid-batch for hard blockers:

- The Obsidian vault path is missing or inaccessible.
- The PDF folder or queue file is missing and cannot be inferred.
- The same source files repeatedly fail in a way that prevents continuing.
- The user requested writing prose, but there are no eligible evidence rows.

For ordinary per-paper uncertainty, keep moving and leave an audit trail in the queue and notes.

## Batch Reading Queue

Use the queue whenever there is more than one paper. The queue prevents skipped, duplicated, or falsely completed reading.

Machine state lives at:

`00_search-strategy/reading-queue.csv`

Obsidian-readable progress lives at:

`00_search-strategy/reading-queue.md`

Queue statuses:

- `pending`: not read yet.
- `in-progress`: currently being read by Codex.
- `complete`: close-reading note saved and eligible evidence rows recorded.
- `needs-review`: full text was read but metadata, extraction, or evidence anchors need human/Codex review.
- `excluded`: intentionally removed from the review corpus.
- `error`: processing failed; include the reason in the queue.

Initialize a queue from a PDF folder:

```bash
python scripts/manage_reading_queue.py init --vault "C:/path/to/vault" --pdf-dir "C:/path/to/pdfs" --recursive
```

Claim the next paper:

```bash
python scripts/manage_reading_queue.py next --vault "C:/path/to/vault"
```

After saving the Obsidian note, mark the item complete:

```bash
python scripts/manage_reading_queue.py mark --vault "C:/path/to/vault" --id "queue-id" --status complete --citekey "Zhang2024Fibrosis" --note-path "C:/path/to/vault/01_reading-notes/Zhang2024Fibrosis.md"
```

Check progress:

```bash
python scripts/manage_reading_queue.py stats --vault "C:/path/to/vault"
```

When processing a batch, repeat:

`next -> full-text reading -> save note -> mark -> stats -> next`.

Do not mark an item `complete` until the Obsidian note meets the close-reading standard and all used claims have source anchors.

## Close-Reading Standard

A paper is "read" only when the note includes:

- Complete metadata: title, authors when available, year, journal, DOI or PMID when available, and citekey.
- Research question and study type.
- Population, samples, models, disease stage, intervention, or comparison groups as applicable.
- Methods and measurements.
- Main findings as separate evidence cards.
- For every main finding: source anchor, evidence type, evidence strength, and a cautious review-ready sentence.
- Mechanism chain when relevant.
- Limitations and non-supported claims.
- Suggested review section placement.

If the full text is unavailable or the paper was only skimmed, set `status: not-eligible` or `status: skimmed`, and do not use it as a citation in drafts.

## Note Template

Use this Markdown shape for each paper:

```markdown
---
citekey: AuthorYearShortTopic
title: ""
year:
journal: ""
doi: ""
pmid: ""
disease: ""
topic: ""
study_type: ""
status: close-read-complete
source_file: ""
---

# Bibliographic Record

# Research Question

# Study Design And Materials
- Population/model:
- Sample size:
- Disease stage/context:
- Groups/intervention:

# Methods

# Main Findings
## Finding 1
- Claim:
- Source anchor:
- Evidence type:
- Evidence strength: strong/moderate/weak
- Review-ready sentence:

## Finding 2
- Claim:
- Source anchor:
- Evidence type:
- Evidence strength:
- Review-ready sentence:

# Mechanism Chain

# Limitations
- Author-stated:
- Reader-assessed:
- Does not support:

# Review Placement

# One-Sentence Value
```

## Evidence Matrix

Maintain `02_evidence-matrix/evidence-matrix.md` as the writing source of truth:

```markdown
| Topic | Claim | Citekey | Source anchor | Evidence type | Strength | Review-ready sentence | Eligible |
|---|---|---|---|---|---|---|---|
```

Only rows with `Eligible` set to `yes` may be used in draft prose. If a claim has no anchor, mark it `no` until verified.

## Obsidian Saving Script

Use `scripts/save_obsidian_note.py` to create notes and append optional matrix rows:

```bash
python scripts/save_obsidian_note.py --vault "C:/path/to/vault" --citekey "Zhang2024Fibrosis" --title "Paper title" --authors "Zhang et al." --year 2024 --journal "Journal" --doi "10.xxxx/xxxx" --topic "hepatic fibrosis" --status close-read-complete --note-file "C:/path/to/generated_note.md" --matrix-row "hepatic fibrosis|Macrophage activation is associated with fibrogenic signaling.|Fig. 2, p. 6|animal model|moderate|Macrophage activation may contribute to fibrogenic signaling in this model.|yes"
```

The `--note-file` must contain the close-reading Markdown body. The script writes the note into `01_reading-notes/`, preserves YAML frontmatter, creates project folders, ensures the evidence matrix exists, and appends each `--matrix-row`.

Each `--matrix-row` uses seven pipe-separated fields:

`Topic | Claim | Source anchor | Evidence type | Strength | Review-ready sentence | Eligible`

If the script is not suitable for the environment, write the Markdown files directly with the same folder structure and schema.

When working from the queue, pass `--source-file` so the note remains linked to the original PDF, then mark the queue item with the saved note path printed by the script.

## Drafting Rules

Before drafting, gather relevant matrix rows and list the citekeys that will support the section. Then write with these constraints:

- Use only completed notes and eligible matrix rows.
- Attach at least one citekey to each substantive claim.
- Preserve uncertainty: do not convert association into causation unless the paper design supports causality.
- Do not generalize cell, animal, or single-cohort results to all liver disease.
- When evidence conflicts, describe the conflict and cite both sides.
- If evidence is insufficient, say so and mark a literature gap instead of filling it.

## Claim Audit

After drafting any section, create a table:

```markdown
| Draft claim | Supporting citekey | Source anchor | Supported? | Overreach risk | Action |
|---|---|---|---|---|---|
```

Flag unsupported claims and either delete, soften, or send them back to close reading. Do not present a section as complete until this audit exists.

## User-Facing Progress Reports

Report progress in evidence terms:

- Number of PDFs processed.
- Queue counts by status.
- Number of close-reading notes created.
- Number of eligible evidence rows.
- Number of papers excluded or marked not eligible.
- Draft sections produced and audit status.

Avoid saying "I read everything" unless every used source has a completed note and source anchors.

## High-impact Hepatology Submission Package

Use this section when the user has a near-final English review and asks for a Journal of Hepatology / Hepatology / Gut-style submission package, final submission files, title page, checklist, or asks "下一步" after final prose and citation cleanup.

### Goal

Create a submission-ready file set without changing the scientific argument:

- Main manuscript Word file.
- Main manuscript Markdown source.
- Title page Word and Markdown files.
- Final submission checklist Word and Markdown files.
- Basic metrics: word count excluding references, number of references, figures, tables, and boxes.
- File-readability validation.
- A clear recommendation that the next high-value step is Figure 1 graphical abstract / circuit map preparation.

### Default File Naming

For Journal of Hepatology-style PSC review projects, prefer these output names:

```text
JHEP_submission_main_manuscript.docx
JHEP_submission_main_manuscript.md
JHEP_title_page.docx
JHEP_title_page.md
JHEP_final_submission_checklist.docx
JHEP_final_submission_checklist.md
```

If the target journal is not JHEP, replace the prefix with the journal short name, for example:

```text
Hepatology_submission_main_manuscript.docx
Gut_submission_main_manuscript.docx
```

### Source Selection

Use the latest clean manuscript as the source. Prefer the most recent file that satisfies all of the following:

- No internal citekeys in the reference list.
- No `Citekey Number Map`.
- No `[REFERENCE NEEDED]`, `[VERIFY DOI]`, or `[VERIFY PUBLICATION STATUS BEFORE SUBMISSION]` markers unless the user explicitly wants a marked working draft.
- Includes the final intended reference set.
- Includes finalized or near-final figure/table legends.

If multiple manuscript versions exist, inspect and report which file is chosen and why. Do not silently choose an older file.

### Metrics To Compute

Always compute and report:

- Approximate word count excluding references.
- Number of numbered references.
- Number of figures.
- Number of tables.
- Number of boxes.

For Markdown sources, count references as lines matching:

```text
^\d+\. 
```

Count figures/tables/boxes by headings such as:

```text
### Figure
### Table
## Box
```

### Title Page Template

Create a title page with these sections:

```markdown
# Title Page

## Manuscript Title

[Full title]

## Short Title

[Short title]

## Article Type

Review

## Authors

[Author 1 full name, degrees]^1
[Author 2 full name, degrees]^2

## Affiliations

^1 [Department, Institution, City, Country]
^2 [Department, Institution, City, Country]

## Corresponding Author

[Name, degrees]
[Department, Institution]
[Full postal address]
Email: [email]
Telephone: [telephone]

## Manuscript Details

- Word count excluding references: approximately [count]
- References: [count]
- Figures: [count]
- Tables: [count]
- Boxes: [count]
- Keywords: [keywords]

## Conflict of Interest Statement

[Author initials] reports [details].
All other authors declare no competing interests.

If none:

The authors declare no competing interests.

## Funding Statement

This work was supported by [funding body, grant number].

If none:

This work received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors.

## Author Contributions

Conceptualization: [initials].
Literature review and evidence synthesis: [initials].
Writing - original draft: [initials].
Writing - review and editing: [initials].
Figures and tables: [initials].
Supervision: [initials].

## Data Availability Statement

No new datasets were generated or analysed for this Review. The cited literature is available from the original publications.

## Ethics Statement

Ethics approval was not required because this article is a Review of previously published literature.
```

### Final Submission Checklist Template

Create a checklist with:

- Current core files table.
- Manuscript metrics.
- Completed items.
- Still needed before actual submission.
- Recommended next step.

For a JHEP/Hepatology-level review, include at minimum:

```markdown
# JHEP Final Submission Checklist

## Current Core Files

| Purpose | File |
|---|---|
| Main manuscript Word file | `JHEP_submission_main_manuscript.docx` |
| Main manuscript Markdown source | `JHEP_submission_main_manuscript.md` |
| Title page | `JHEP_title_page.docx` |
| Cover letter | `cover_letter_draft.docx` |
| Submission statements template | `submission_statements_template.docx` |
| Evidence audit | `[audit file]` |

## Manuscript Metrics

- Word count excluding references: approximately [count]
- References: [count]
- Figures: [count]
- Tables: [count]
- Boxes: [count]

## Completed

- Circuit-model thesis preserved.
- Reference list cleaned of internal citekeys.
- Citation evidence audit completed or available.
- Figures/tables counted and named.
- Word file exported and checked for readability.

## Still Needed Before Actual Submission

1. Fill in author names, affiliations, corresponding author details, funding, COI, and author contributions in the title page.
2. Decide whether to trim word count if the journal enforces a strict word limit.
3. Prepare actual figure artwork or verify final high-resolution figure files.
4. Convert figure legends from design-oriented wording into final descriptive legends after artwork is created.
5. Recheck any ahead-of-print references for final volume/page details immediately before submission.
6. Confirm journal reference style requirements.
7. Check whether the journal requires separate upload files for tables, figures, graphical abstract, highlights, or supplementary material.

## Recommended Next Step

Prepare Figure 1 as a graphical abstract-style circuit map. This is the most important display item for editor triage because it communicates the manuscript's core novelty at a glance.
```

### Validation

After creating the files:

- Verify Word files can be opened by `python-docx`.
- Report paragraph and table counts for the main manuscript.
- Verify title page and checklist open correctly.
- Do not claim the files are submission-ready if placeholders remain for author details, COI, funding, or contributions.

### User-facing Summary

When reporting completion, include:

- Links or paths to the main manuscript, title page, and checklist.
- Current metrics.
- Validation result.
- The next recommended action: Figure 1 graphical abstract / circuit map, unless the user has already requested a different next step.
