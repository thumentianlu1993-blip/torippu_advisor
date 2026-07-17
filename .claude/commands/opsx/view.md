---
name: "OPSX: View"
description: Display an interactive dashboard of specs and changes
category: Workflow
tags: [workflow, status, dashboard]
---

Display an interactive dashboard overview of all OpenSpec specs and changes.

**Input**: None required.

**Steps**

1. **Launch the interactive dashboard**

   ```bash
   openspec view
   ```

   This opens a terminal-based interactive dashboard showing:
   - All active changes with their status
   - All specs with their current state
   - Navigation between items

2. **If the terminal does not support interactive mode**, fall back to:

   ```bash
   openspec list --json
   openspec list --specs --json
   ```

   Then display a combined summary of changes and specs in text format.

**Output**

Interactive terminal dashboard, or a text-based summary if interactive mode is unavailable.

**Guardrails**
- Prefer interactive mode when available
- Fall back gracefully to text output
