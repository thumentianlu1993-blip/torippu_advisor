---
name: grill-me-codex
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving every material branch of the decision tree before design review or implementation. Use when the user asks to stress-test a plan, requests a decision interview, or mentions "grill me".
user-invocable: true
disable-model-invocation: true
---

# Grill Me for Codex

Interview the user relentlessly about every material aspect of the plan until both sides reach a shared understanding. Resolve dependencies between decisions one by one and provide a recommended answer for every question.

## Required workflow

1. Before asking a question, inspect the repository and its documentation whenever the answer can be confirmed from existing code, configuration, tests, migrations, or prior project decisions. Do not ask the user to rediscover facts that the repository can establish.
2. Maintain a decision tree internally. Ask the highest-leverage unresolved question whose answer is required before downstream choices can be resolved.
3. Ask exactly one critical question at a time using `request_user_input`, then wait for the user's answer before continuing. Never batch questions.
4. For every question, concisely include:
   - the current code and product state established by exploration;
   - why the decision is necessary now and which later decisions it blocks;
   - mutually exclusive options and the concrete impact of each;
   - security, privacy, data-integrity, compatibility, and migration risks where relevant;
   - relative implementation and operational cost;
   - the recommended option and the reason for recommending it.
5. Challenge vague terms, conflicting assumptions, hidden edge cases, and answers that contradict the repository. Use concrete scenarios when they expose important boundary conditions.
6. Record answers only through the project's required change-document workflow. Do not create or write `PLAN.md`.
7. Continue until all material decisions required for the scoped spec and design are resolved. Explicitly preserve `unresolved` for any decision the user has not made.

## Hard gates

- This skill is for exploration and decision clarification only. Do not implement product changes, write implementation tests, refactor code, commit, push, create a pull request, deploy, or perform production writes.
- Do not begin or approve solution review while a material decision for the scoped change remains unresolved.
- Do not begin testing or implementation while solution review remains incomplete.
- Follow repository instructions and the project's mandated exploration, spec/design, review, test-first, subagent implementation, code-review, and explicitly authorized release gates.
- If `request_user_input` is unavailable in the current session, stop and explain that Codex must reload the project or start a new session after enabling the feature. Do not silently replace the required interaction with a batch questionnaire.
