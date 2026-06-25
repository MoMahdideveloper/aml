# Deep Think Stage P1: Critical-path triage

## Objective
Critical-path triage

## Primary Question
Given these failures, what is the minimum dependency-ordered fix sequence to restore all critical flows without regressions?

## Required Output Format
- Priority table with top blockers
- Dependency ordering and minimal patch strategy
- Concrete affected files per blocker
- At least one regression test per blocker

## Context Chunks
- Reference only the chunk IDs listed in `prompt_chain.level1.template.json`.
- Paste curated code excerpts (not full files).

