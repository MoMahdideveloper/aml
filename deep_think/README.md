# Deep Think Workflow

This folder contains semi-automated artifacts for running Gemini Deep Think against this codebase.

## Generate Artifacts

```powershell
python scripts/deep_think_workflow.py generate
```

This creates:

- `deep_think/context_manifest.json`
- `deep_think/prompt_chain.json`
- `deep_think/deep_think_session.md`
- `deep_think/prompts/P1.md` ... `deep_think/prompts/P5.md`

## Open Gemini With Cookies (MCP Playwright)

1. Keep cookies in-memory only (do not commit cookie files).
2. If needed, emit normalized `browser_run_code` JS:

```powershell
python scripts/deep_think_workflow.py emit-cookie-js --cookies-file <path-to-cookie-json>
```

3. Run that JS with MCP `browser_run_code`.
4. Confirm URL resolves to `https://gemini.google.com/app` and chat UI is available.

## Stage Execution (Semi-Automated)

1. Open prompt file `deep_think/prompts/Px.md`.
2. Paste to Gemini Deep Think and wait for completion.
3. Save response to a local text/markdown file (outside git if preferred).
4. Append response:

```powershell
python scripts/deep_think_workflow.py append-response --stage P1 --response-file <response.md> --response-link <optional-link>
```

Repeat for `P2` ... `P5`.

## Build Backlog

```powershell
python scripts/deep_think_workflow.py build-backlog
```

Outputs:

- `deep_think/implementation_backlog.json`
- `deep_think/implementation_backlog.md`

## Security Notes

- Cookies and auth state must be runtime-only.
- Do not commit cookie dumps or Playwright storage state.
- Context generation includes basic key/token/password redaction before prompt packaging.
