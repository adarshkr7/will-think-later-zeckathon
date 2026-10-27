# PRAHARI

**P**oint-in-time **R**isk & **A**ccounting **H**azard **A**lerts, **R**anked & **I**nterpretable. *Prahari* is Hindi for "sentinel".

A submission for **Zeckathon PS-02 (Risk & Fraud)**: an early-warning system for Indian corporate credit that would have caught IL&FS.

## What it does

PRAHARI is a "credit-desk time machine". Pick any past quarter and it rebuilds what the market and filings showed on that date, using only documents published by then. It ranks ~800 indebted listed borrowers and produces a watch-list capped at 5% of the universe, each name with a short, template-generated credit memo. We then check which later defaulters were already flagged 4 and 8 quarters before default.

Key properties:

- **No look-ahead.** Every feature row carries a `public_date`; scoring at date *t* only sees rows published before *t*, enforced by tests.
- **Pre-registered evaluation.** Configs, weights and peer lists are hashed and committed before Indian labels are read.
- **Cost-optimal policy under a hard cap.** Threshold minimises `20·FN + FP` while never exceeding the 5% review budget.
- **Exact, auditable explanations.** Additive log-odds attributions grouped into credit pillars, rendered by deterministic templates. No LLMs in the pipeline.
- **Separate scorecard for financial firms** (NBFCs, HFCs), where Altman/Beneish don't apply.

## Repository guide

| File | Purpose |
|---|---|
| `ps.pdf` | Problem statement and judging criteria |
| `PROJECT_IDEA.md` | What we are building and why |
| `IMPLEMENTATION_PLAN.md` | Phases, modules, tests and acceptance checks |
| `AGENTS.md` | Operating rules for coding agents working on this repo |

## Status

Planning stage. Code, configs, and the pipeline (`run_all.ps1`, `run_tests.ps1`) will be added phase by phase per `IMPLEMENTATION_PLAN.md`.

## Environment

Windows 11, Python 3.11, virtualenv at `.venv`.
