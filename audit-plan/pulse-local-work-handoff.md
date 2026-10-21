# Work Local handoff: complete Pulse audit remediation

Repository: `https://github.com/pablopovar/pulse`

## Objective

Assemble the existing remediation branches and implement all remaining active audit findings in `pulse-app/`.

Do not test during implementation. Once the complete change set exists, stop so Pablo and Work Local can test the running software together in one session.

## Exact starting state

Common base:

```text
5b4148c0e24030494fca8609e0180ab3a4b0fc9d
```

Existing remediation heads:

```text
fix/report-run-identity       e7d4a4a54f98a8f8ee933dd3bc26eadf2485d3d7
fix/access-domain-boundaries  39a2e17ac37f65561d42f79f3c006f48891ac2ce
audit-plan                    3c7977f11ec7d7607ab6a96356854c251186fa4c
```

Draft pull requests:

- PR #5: `https://github.com/pablopovar/pulse/pull/5`
- PR #6: `https://github.com/pablopovar/pulse/pull/6`

There is no remote `fix/full-audit` branch. Create it locally.

## Create the working branch

Use a clean worktree.

```bash
cd /path/to/pulse

git fetch origin \
  main \
  audit-plan \
  fix/report-run-identity \
  fix/access-domain-boundaries

git switch -c fix/full-audit origin/fix/report-run-identity
git merge --no-ff origin/fix/access-domain-boundaries
```

If the clone is shallow and Git cannot find the common base:

```bash
git fetch --unshallow origin
git merge --no-ff origin/fix/access-domain-boundaries
```

Read the audit plan without merging its documentation branch:

```bash
git show origin/audit-plan:audit-plan/pulse-app-audit-plan.md
```

## Proposed remediations already present

The assembled branch contains changes intended to address:

```text
F01 F03 F06 F10 F14 F21 F29 F30 F33
```

Treat these as implemented but unverified. Preserve the existing test files. Do not run them or add more tests during this pass.

## Remaining findings

Implement exactly:

```text
F02 F04 F05 F07 F08 F09 F11 F12
F13 F15 F16 F17 F18 F19 F20 F22
F23 F24 F25 F26 F27 F28 F32 F34
```

F31 was withdrawn and requires no change.

## Decisions to apply

- **F02:** Password rotation or replacement revokes prior browser grants. Bind authorization to the current policy version.
- **F08:** Never return unscoped legacy keyword data. If site scope cannot be proven, expose the source as unavailable with a clear reason.
- **F17:** Keep the scoring formula, but show evaluated count, applicable count, and coverage beside every score.
- **F19:** Connection status and report selection are independent. Connected sources may be deselected.
- **F22:** Historical paid evidence may be displayed only when explicitly identified as historical supplemental evidence. It must not appear as current-run evidence.
- **F23:** A report-quality result marked `blocking` prevents publication and leaves the prior report current.
- **F27:** Confirmed failures and unevaluated signals receive separate PDF sections. Unevaluated rows cannot consume the confirmed-finding quota.
- **F28:** Apply persisted exclusions as a presentation overlay to HTML, PDF, and exports. Preserve the immutable underlying observation.
- **F32:** Comparison controls use complete normalized observations. Material-change history remains a separate compact view.

For conditional findings such as F05 and F08, implement the defensive boundary without claiming that the failure occurred in production.

## Scope and constraints

- Work only in `pulse-app/`.
- Do not modify `opengsc`.
- Do not re-audit tests or migration history.
- Do not write new tests.
- Do not run tests, linters, compilers, migrations, containers, services, browsers, or application commands.
- Do not delete existing tests from the merged branches.
- A new migration is allowed only if a remediation genuinely requires schema evolution. Record why it is unavoidable.
- Preserve raw evidence. Correct selection, attribution, interpretation, and presentation around it.
- Do not merge, deploy, or push unless Pablo separately requests it.
- Commit coherent implementation batches locally.
- Do not stop after producing another plan.

## Required implementation ledger

Maintain one row per finding:

```text
Finding | Files changed | Behavior before | Behavior after | Assumption or limitation
```

Do not label a finding `verified` during this pass. Valid states are:

```text
implemented, blocked, or requires external schema/runtime evidence
```

A blocked finding must include the exact code or external dependency preventing implementation.

## Stop point

After all 24 remaining findings have been addressed:

1. Inspect the complete diff statically.
2. Reconcile all 33 active findings against the ledger.
3. Report any blockers without disguising them as fixes.
4. Record schema and configuration implications.
5. Provide one ordered software-level test script covering the complete application.
6. Stop before executing that script.
