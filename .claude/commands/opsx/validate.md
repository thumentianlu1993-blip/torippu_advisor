---
name: "OPSX: Validate"
description: Validate changes and specs for correctness
category: Workflow
tags: [workflow, validation, ci]
---

Validate OpenSpec changes and specs for correctness and completeness.

**Input**: Optionally specify an item name (e.g., `/opsx:validate add-auth`). If omitted, validates all active changes.

**Steps**

1. **Run validation**

   If a specific item is provided:
   ```bash
   openspec validate "<name>" --json
   ```

   If no item specified, validate all:
   ```bash
   openspec validate --json
   ```

2. **Parse and display results**

   Show validation results as a checklist:
   - Artifact structure completeness
   - Required fields present
   - Dependency consistency
   - Task format correctness

3. **On validation failure**, show specific errors with file paths and line references so the user can fix them.

4. **On success**, confirm all checks passed.

**Output On Success**

```
## Validation Passed

All checks passed for: <name>
- ✓ Artifact structure complete
- ✓ Required fields present
- ✓ Dependencies consistent
- ✓ Task format correct
```

**Output On Failure**

```
## Validation Failed

**Change:** <name>
**Errors:** 2

1. Missing required field `goal` in proposal.md (line 5)
2. Task format invalid in tasks.md (line 12): missing checkbox

Fix these issues and run `/opsx:validate <name>` again.
```

**Guardrails**
- Show actionable error messages with file paths
- Suitable for CI integration: `openspec validate` can be added to pre-commit or CI pipelines
