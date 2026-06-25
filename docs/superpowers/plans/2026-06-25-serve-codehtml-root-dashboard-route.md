# Serve code.html as Root Page and Move Dashboard to /dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve the existing code.html file as the root page (/) and move the current dashboard to /dashboard route, making both accessible.

**Architecture:** Modify the main blueprint in views/main.py to add a new route handler for '/' that reads and returns the content of code.html directly, and change the existing dashboard route from '/' to '/dashboard'. No changes to the file location or template structure.

**Tech Stack:** Flask, Python, HTML

---
### Task 1: Backup original views/main.py

**Files:**
- Create: `docs/superpowers/plans/2026-06-25-serve-codehtml-root-dashboard-route_backup/main.py` (optional backup)
- Modify: `views/main.py`

- [ ] **Step 1: Copy views/main.py to a backup location**

```bash
cp views/main.py views/main.py.bak
```

- [ ] **Step 2: Verify backup exists**

Run: `ls -la views/main.py.bak`
Expected: File exists with same size as original

- [ ] **Step 3: Commit backup**

```bash
git add views/main.py.bak
git commit -m "chore: backup main.py before route changes"
```
### Task 2: Add new root route to serve code.html

**Files:**
- Modify: `views/main.py`

- [ ] **Step 1: Import send_file and os if not already imported**

Check current imports at top of file. If `send_file` not imported, add it.

```python
# After existing imports, ensure these are present:
from flask import send_file
import os
```

If already present, skip.

- [ ] **Step 2: Write the new root route function**

Insert above or below existing dashboard function (we'll place it before dashboard for clarity):

```python
@bp.route('/')
@bp.route('/')
def root_route function:

```python
@bp.route('/')
@log_execution
@log_execution
def serve_code_html():
    """Serve the code.html file as the root page."""
    try:
        file_path = os.path.join(
            os.path.dirname(__file__),
            'stitch_kpi_performance_dashboard',
            'dashboard_overview',
            'code.html'
        )
        return send_file(file_path, mimetype='text/html')
    except FileNotFoundError:
        return "File not found: code.html", 404
    except Exception as e:
        # Log the error (optional)
        return f"Error reading file: {str(e)}", 500
```

- [ ] **Step 3: Run a quick syntax check to ensure no import errors**

Run: `python -m py_compile views/main.py`
Expected: No output (success)

- [ ] **Step 4: Commit the changes**

```bash
git add views/main.py
git commit -m "feat: add root route to serve code.html"
```
### Task 3: Move existing dashboard route to /dashboard

**Files:**
- Modify: `views/main.py`

- [ ] **Step 1: Locate the existing dashboard function**

Find the function decorated with `@bp.route('/')` (currently line 41).

- [ ] **Step 2: Change the route decorator from '/' to '/dashboard'**

Replace:

```python
@bp.route('/')
```

with:

```python
@bp.route('/dashboard')
```

- [ ] **Step 3: Optionally keep the same function name (dashboard) or rename; we keep name**

No other changes needed.

- [ ] **Step 4: Verify the function still works**

Run: `python -m py_compile views/main.py`
Expected: No output (success)

- [ ] **Step 5: Commit the changes**

```bash
git add views/main.py
git commit -m "feat: move dashboard route to /dashboard"
```
### Task 4: Test the changes manually (optional but recommended)

**Files:**
- None (temporary)

- [ ] **Step 1: Start the Flask development server**

Run: `python main.py` (in background or separate terminal)

- [ ] **Step 2: Visit http://127.0.0.1:5000/ in a browser**
Expected: See the content of code.html (Luxe Estate dashboard)

- [ ] **Step 3: Visit http://127.0.0.1:5000/dashboard**
Expected: See the original CRM dashboard (properties, deals, etc.)

- [ ] **Step 4: Stop the server**

Press Ctrl+C in the terminal where it's running.

- [ ] **Step 5: Commit any test-related changes if needed (none)**

```bash
# No changes to commit; just cleanup if any test files were created
```
### Task 5: Run existing tests to ensure no regression

**Files:**
- Test: `tests/` (existing test suite)

- [ ] **Step 1: Run the test suite**

Run: `python -m pytest -q`
Expected: All tests pass (or at least no new failures due to our changes)

- [ ] **Step 2: If any tests fail, investigate and fix**

(If failures occur, we would need to adjust; but since we only changed routes and didn't break existing functionality, tests should pass.)

- [ ] **Step 3: Commit if any fixes were made**

```bash
git add .
git commit -m "fix: adjust tests if needed"
```
### Task 6: Final verification and cleanup

**Files:**
- None

- [ ] **Step 1: Remove backup file if desired (optional)**

```bash
rm views/main.py.bak
```

- [ ] **Step 2: Commit removal**

```bash
git add views/main.py.bak
git commit -m "chore: remove backup file"
```
 OR keep backup for safety.

- [ ] **Step 2: Ensure plan is complete**

All tasks done.

Now we can move to execution.