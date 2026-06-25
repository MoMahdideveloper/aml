# PropTech Brain Deep Think Pack

This pack prepares a project-specific prompt chain for the next architecture wave:

- Smart Context Engine (silver-lining benefits + trend badges)
- Dual-Sided Scoring (customer + property)
- Matchmaker + Copilot pitch drafting
- Weekly trend/training pipeline

All prompts are constrained by existing `gptvli` contracts:

- API/XHR unauthorized must be `401/403` JSON (no redirect leakage)
- CSRF must remain enforced (no blanket exemptions)
- Deterministic fallback when Gemini/vector paths fail
- Keep existing public routes/contracts backward compatible

Files:
- `context_manifest.json`
- `prompt_chain.json`
- `prompts/PB1.md` ... `prompts/PB6.md`
- `session.md`

