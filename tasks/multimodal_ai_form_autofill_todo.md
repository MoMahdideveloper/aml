# Todo: Multimodal AI Form Autofill

Source spec: `docs/superpowers/specs/2026-07-11-multimodal-ai-form-autofill-design.md`  
Implementation plan: `docs/superpowers/plans/2026-07-11-multimodal-ai-form-autofill.md`

## Phase 1: Deterministic Core

- [x] Task 1: Define typed extraction contracts and allowlisted form registry.
- [x] Task 2: Implement Persian value normalization.
- [x] Task 3: Implement confidence, no-overwrite, and conflict policy.

### Checkpoint A

- [x] All registry fields map to active CRM inputs.
- [x] Persian normalization tests pass.
- [x] Confidence boundary tests pass at 0.90 and 0.70.
- [ ] Human approves registry before provider/database work.

## Phase 2: Provider and Audit Foundation

- [ ] Task 4: Add mocked, structured text/image/audio Gemini extractor.
- [ ] Task 5: Add audit models and disposable-verified Alembic migration.
- [ ] Task 6: Add private checksummed media storage.

### Checkpoint B

- [ ] No external calls occur in automated tests.
- [ ] Migration upgrade/downgrade/re-upgrade passes on disposable DB.
- [ ] Audit media cannot be served from `static/`.
- [ ] Human approves migration, storage, and 90-day retention.

## Phase 3: Property Vertical Slice

- [ ] Task 7: Add authenticated, CSRF-protected extraction/review API.
- [ ] Task 8: Add reusable multimodal input and review panel.
- [ ] Task 9: Integrate Property create/edit forms end-to-end.

### Checkpoint C

- [ ] Property text/image/audio workflow passes with mocked Gemini.
- [ ] Existing Property save path remains unchanged.
- [ ] Existing non-empty values never auto-overwrite.
- [ ] Human approves Property UX before expansion.

## Phase 4: Remaining Forms

- [ ] Task 10: Customer and recommendation-preference slice.
- [ ] Task 11: Deal and Task slice.
- [ ] Task 12: Agent slice.

### Checkpoint D

- [ ] Every schema maps to active form controls.
- [ ] Relationship references are review-only and resolved server-side.
- [ ] Existing CRUD/form tests pass.
- [ ] Desktop/mobile/accessibility review passes.

## Phase 5: Operations and Release Gate

- [ ] Task 13: Add retention and authorized audit cleanup.
- [ ] Task 14: Add configuration, readiness behavior, and operator docs.
- [ ] Task 15: Run full AI, Track A, security, migration, and browser verification.

### Final Gate

- [ ] Persian text, image, and audio extraction works.
- [ ] Confidence hybrid follows approved thresholds.
- [ ] User review and normal form save remain mandatory.
- [ ] Audit content is private and retention-managed.
- [ ] Provider failures do not break ordinary forms.
- [ ] Automated tests make no paid Gemini calls.
- [ ] Production and unrelated dirty paths remain untouched.
- [ ] Human separately approves any commit, push, production migration, or deployment.
