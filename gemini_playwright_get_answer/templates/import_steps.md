# Import Steps (Quick)

1. Create target folder in new project:
   - `deep_think/`
   - `deep_think/prompts/`
   - `deep_think/responses/`
2. Copy these templates:
   - `context_manifest.level1.template.json` -> `deep_think/context_manifest.json`
   - `prompt_chain.level1.template.json` -> `deep_think/prompt_chain.json`
   - `P1_prompt.template.md` -> `deep_think/prompts/P1.md`
   - `deep_think_session.template.md` -> `deep_think/deep_think_session.md`
3. Fill context chunks from the new project codebase.
4. Run Playwright bootstrap using `playwright_cookie_bootstrap.template.js`.
5. Submit P1 prompt in Gemini Deep Think, then capture response into session log.

