# Gemini Playwright Get Answer Pack

Reusable pack for running staged Gemini Deep Think sessions with Playwright MCP in other projects.

## Folder Structure
- `level_1_copy/`: direct copy of Level 1 assets from this conversation/project.
- `templates/`: clean starter templates for new projects.

## Level 1 Copy
- `level_1_copy/P1_prompt_copy.md`
- `level_1_copy/P1_response_manual_summary_copy.md`
- `level_1_copy/prompt_chain_full_copy.json`
- `level_1_copy/context_manifest_full_copy.json`
- `level_1_copy/deep_think_session_snapshot_copy.md`

## Import In Another Project
1. Copy this folder into your target repository.
2. Duplicate files from `templates/` into the target project's `deep_think/` folder.
3. Replace placeholder context chunks with that project's files.
4. Use Playwright MCP cookie bootstrap from `templates/playwright_cookie_bootstrap.template.js`.
5. Start with `P1` prompt and continue stage-by-stage.

