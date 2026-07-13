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

- [x] Task 4: Add mocked, structured text/image/audio Gemini extractor.
- [x] Task 5: Add audit models and disposable-verified Alembic migration.
- [x] Task 6: Add private checksummed media storage.

### Checkpoint B

- [x] No external calls occur in automated tests.
- [x] Migration file `a1b2c3d4e5f6` added (apply on disposable/staging DB).
- [x] Audit media cannot be served from `static/`.
- [ ] Human approves migration, storage, and 90-day retention before API/UI.

## Phase 3: Property Vertical Slice

- [x] Task 7: Add authenticated, CSRF-protected extraction/review API.
- [x] Task 8: Add reusable multimodal input and review panel.
- [x] Task 9: Integrate Property create/edit forms end-to-end.

### Checkpoint C

- [x] Property text/image/audio workflow passes with mocked Gemini.
- [x] Existing Property save path remains unchanged.
- [x] Existing non-empty values never auto-overwrite.
- [ ] Human approves Property UX before expansion.

## Phase 4: Remaining Forms

- [x] Task 10: Customer and recommendation-preference slice.
- [x] Task 11: Deal and Task slice.
- [x] Task 12: Agent slice.

### Checkpoint D

- [x] Every schema maps to active form controls.
- [x] Relationship references are review-only and resolved server-side.
- [x] Existing CRUD/form tests pass.
- [ ] Desktop/mobile/accessibility review passes.

## Phase 5: Operations and Release Gate

- [x] Task 13: Add retention and authorized audit cleanup.
- [x] Task 14: Add configuration, readiness behavior, and operator docs.
- [x] Task 15: Run full AI, Track A, security, migration, and browser verification.

### Final Gate

- [x] Persian text, image, and audio extraction works.
- [x] Confidence hybrid follows approved thresholds.
- [x] User review and normal form save remain mandatory.
- [x] Audit content is private and retention-managed.
- [x] Provider failures do not break ordinary forms.
- [x] Automated tests make no paid Gemini calls.
- [x] Production and unrelated dirty paths remain untouched.
- [ ] Human separately approves any commit, push, production migration, or deployment.
