---
name: "OPSX: List"
description: List OpenSpec changes and/or main specs at a glance
category: Workflow
tags: [workflow, list, experimental]
---

List OpenSpec changes and main specs.

**Input**: Optional filter after `/opsx:list`:
- (empty) — list both active changes and main specs
- `changes` — only active changes
- `specs` — only main specs
- `archive` — also include archived changes
- `all` — everything (active changes + archive + specs)

**Steps**

1. **Decide scope from the argument** (default `both`).

2. **Run the relevant openspec CLI calls in parallel via Bash:**

   - For active changes: `openspec list --json`
   - For main specs: `openspec list --specs --json`
   - For archived changes (only if scope includes archive/all): `ls openspec/changes/archive` (the CLI does not list archive directly)

   If `--json` is not supported by the installed openspec version, fall back to the plain `openspec list` / `openspec list --specs` output.

3. **Render output as markdown tables.**

   **Active changes table** columns: name • tasks completed / total • last-modified (relative).
   **Main specs table** columns: name • requirements count (if available).
   **Archive list**: just bullet names with their date prefix.

   Sort active changes by recency (most recent first). Sort specs alphabetically. Sort archived changes by date prefix descending.

4. **End with a one-line next-step hint** depending on what was shown:

   - If active changes exist: "Tip: `/opsx:apply <name>` to start implementing, `/opsx:archive <name>` to archive a completed one."
   - If only specs were requested: "Tip: `openspec show <spec-name>` to view a spec in detail."
   - If nothing exists in scope: tell the user the directory is empty and suggest `/opsx:propose` to create the first change.

**Rules**

- Do NOT propose, modify, or archive anything. This command is read-only.
- Do NOT spawn an agent — single-shot CLI invocations are enough.
- Do NOT run the heavier `openspec view` interactive dashboard — it is for humans, not for parsing.
- If `openspec` CLI is missing, tell the user it is not installed and stop. Do not try to install it implicitly.
