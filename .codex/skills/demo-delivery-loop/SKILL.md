---
name: demo-delivery-loop
description: Drive the hackathon demo through implementation, test, browser verification, completion reporting, secret/data checks and final private GitHub delivery without stopping at partial progress.
---

# Demo Delivery Loop

## When to use

Use this skill for the main implementation session and for final delivery. It turns the target into a sequence of verified deliverables rather than an unfinished code draft.

## Loop

1. Read `AGENTS.md` and `docs/DEMO_ACCEPTANCE.md`.
2. Inspect repository state and record the existing run commands.
3. Implement the smallest next missing acceptance item.
4. Run the relevant tests/build checks immediately.
5. Fix failures rather than documenting them as future work.
6. Launch frontend and backend locally; exercise the browser flow or equivalent automated smoke test.
7. Update `docs/DEMO_COMPLETION_REPORT.md` with actual commands and results.
8. Repeat steps 3-7 until all required acceptance items pass.

Do not conclude with “next steps” while a mandatory checkbox remains incomplete, unless blocked by credentials or an external service. A credentials block affects only GitHub push; it does not justify leaving local demo acceptance unfinished.

## Final checks before GitHub

- Confirm no real patient data exists.
- Confirm no `.env`, tokens, credentials, build caches, virtual environments or local databases are tracked.
- Confirm README run commands work from a clean checkout.
- Confirm tests/build checks pass.
- Record screenshots or a brief demo walkthrough path.
- Commit changes coherently.

## GitHub delivery

If GitHub CLI is installed and authenticated, create a **private** repository named `zgcHack` from the finished local repository and push the validated branch. Do not fabricate success: report the exact repository creation/push command result. If authentication is unavailable, finish all local work and report the single authentication action required for the user to authorize publishing.
