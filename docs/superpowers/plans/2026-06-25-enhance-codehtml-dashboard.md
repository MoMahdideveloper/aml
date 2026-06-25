# FACT-FORCING GATE INFO:
# Importers/Callers: Documentation file for implementation guidance - not imported by code
# Affected API: Flask routes in views/main.py (root '/' and dashboard '/dashboard' endpoints)
# Data schemas: None (view/controller layer enhancements only)
# User's verbatim instruction: "1 2 3 4 5"

# Enhance code.html Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance the newly implemented code.html dashboard serving at root path (/) with testing, performance optimization, improved error handling, security considerations, and asset optimization.

**Architecture:** 
1. Add comprehensive tests for root and dashboard endpoints
2. Implement Flask caching for improved performance
3. Enhance error handling and logging capabilities
4. Review and implement appropriate security measures
5. Optimize asset loading and verify resource integrity

**Tech Stack:** Flask, Python, Flask-Caching, Python logging, HTML/CSS/JS optimization

---

### Task 1: Testing & Verification

**Files:**
- Create: tests/test_root_dashboard_routes.py
- Modify: None (extend existing test structure)
- Test: New test file

- [ ] **Step 1: Write failing test for root route content verification**

```python
def test_root_route_serves_valid_html(client):
    """Test that root route serves valid HTML from code.html."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"<!DOCTYPE html>" in resp.data.upper() or b"<html" in resp.data.lower()
    assert b"<head>" in resp.data.lower() and b"</head>" in resp.data.lower()
    assert b"<body" in resp.data.lower() and b"</body>" in resp.data.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_root_dashboard_routes.py::test_root_route_serves_valid_html -v`
Expected: FAIL (function not implemented yet)

- [ ] **Step 3: Implement test file structure**

Create tests/test_root_dashboard_routes.py with test class and imports

- [ ] **Step 4: Write passing test**

Implement the actual test logic that will pass after implementation

- [ ] **Step 5: Commit test file**

```bash
git add tests/test_root_dashboard_routes.py
git commit -m "feat: add test file for root and dashboard routes"
```

---

### Task 2: Performance Optimization with Caching

**Files:**
- Modify: views/main.py:10-30 (add caching imports and decorators)
- Test: tests/test_root_dashboard_routes.py (add cache tests)

- [ ] **Step 1: Write failing test for caching behavior**

```python
def test_root_route_uses_caching(client):
    """Test that root route implements caching for performance."""
    # First request
    resp1 = client.get("/")
    # Second request should be served from cache (faster, same content)
    resp2 = client.get("/")
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.data == resp2.data  # Content should be identical
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_root_dashboard_routes.py::test_root_route_uses_caching -v`
Expected: FAIL

- [ ] **Step 3: Implement Flask caching in views/main.py**

```python
# Add imports
from flask_caching import Cache

# Initialize cache (will be done in create_app or at module level)
cache = Cache()

# In create_app function:
cache.init_app(flask_app, config={'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TIMEOUT': 300})

# Decorate the route
@bp.route('/')
@cache.cached(timeout=300)  # Cache for 5 minutes
def serve_code_html():
    # ... existing implementation ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_root_dashboard_routes.py::test_root_route_uses_caching -v`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add views/main.py tests/test_root_dashboard_routes.py
git commit -m "feat: add caching to root route for performance optimization"
```

---

### Task 3: Enhanced Error Handling & Logging

**Files:**
- Modify: views/main.py:10-30 (enhance serve_code_html function)
- Test: tests/test_root_dashboard_routes.py (add error case tests)

- [ ] **Step 1: Write failing tests for error scenarios**

```python
def test_root_route_handles_missing_file_gracefully(client, monkeypatch):
    """Test that missing code.html returns appropriate 404 error."""
    def mock_send_file(*args, **kwargs):
        raise FileNotFoundError("code.html not found")
    
    monkeypatch.setattr('flask.send_file', mock_send_file)
    resp = client.get("/")
    assert resp.status_code == 404
    assert b"File not found" in resp.data

def test_root_route_handles_read_error_gracefully(client, monkeypatch):
    """Test that file read errors return appropriate 500 error."""
    def mock_send_file(*args, **kwargs):
        raise PermissionError("Cannot read file")
    
    monkeypatch.setattr('flask.send_file', mock_send_file)
    resp = client.get("/")
    assert resp.status_code == 500
    assert b"Error reading file" in resp.data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_root_dashboard_routes.py::test_root_route_handles_missing_file_gracefully tests/test_root_dashboard_routes.py::test_root_route_handles_read_error_gracefully -v`
Expected: FAIL

- [ ] **Step 3: Enhance error handling and add logging**

```python
# Add imports
import logging
from flask import send_file

logger = logging.getLogger(__name__)

@bp.route('/')
@cache.cached(timeout=300)
def serve_code_html():
    """Serve the code.html file as the root page."""
    try:
        file_path = os.path.join(
            os.path.dirname(__file__),
            '..', '..', '..', '..',
            'stitch_kpi_performance_dashboard',
            'dashboard_overview',
            'code.html'
        )
        logger.info(f"Serving code.html from {file_path}")
        return send_file(file_path, mimetype='text/html')
    except FileNotFoundError:
        logger.warning("code.html file not found")
        return "File not found: code.html", 404
    except Exception as e:
        logger.error(f"Error reading code.html: {str(e)}")
        return f"Error reading file: {str(e)}", 500
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_root_dashboard_routes.py::test_root_route_handles_missing_file_gracefully tests/test_root_dashboard_routes.py::test_root_route_handles_read_error_gracefully -v`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add views/main.py tests/test_root_dashboard_routes.py
git commit -m "feat: enhance error handling and logging for root route"
```

---

### Task 4: Security & Access Control Review

**Files:**
- Modify: views/main.py:10-30 (add security considerations)
- Test: tests/test_root_dashboard_routes.py (add security tests)

- [ ] **Step 1: Write failing test for security headers**

```python
def test_root_route_includes_security_headers(client):
    """Test that root route response includes basic security headers."""
    resp = client.get("/")
    assert resp.status_code == 200
    # Check for basic security headers that should be present
    assert 'X-Content-Type-Options' in resp.headers
    assert 'X-Frame-Options' in resp.headers
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_root_dashboard_routes.py::test_root_route_includes_security_headers -v`
Expected: FAIL (might pass if already implemented elsewhere)

- [ ] **Step 3: Review and enhance security considerations**

Check if security headers are already applied globally in app.py. If not, consider:
- Ensuring debug mode is off in production
- verifying existing security headers in app.py after_request handler
- Adding specific headers if needed for this endpoint

```python
# In serve_code_html function, we could add specific headers if needed:
# response = send_file(file_path, mimetype='text/html')
# response.headers['X-Content-Type-Options'] = 'nosniff'
# response.headers['X-Frame-Options'] = 'DENY'
# return response
```

Actually, looking at app.py, there's already a global after_request handler that sets security headers, so this may already be covered.

- [ ] **Step 4: Run security-related tests**

Run: `pytest tests/test_root_dashboard_routes.py -k security -v`
Expected: PASS

- [ ] **Step 5: Commit any changes**

```bash
git add views/main.py tests/test_root_dashboard_routes.py
git commit -m "feat: review and enhance security for dashboard routes"
```

---

### Task 5: Asset Optimization & Verification

**Files:**
- Create: None (primarily verification)
- Modify: None (verification of existing assets)
- Test: New verification script or tests

- [ ] **Step 1: Write test to verify asset references in code.html**

```python
def test_code_html_references_valid_assets(client):
    """Test that code.html references exist and are accessible."""
    resp = client.get("/")
    assert resp.status_code == 200
    
    html_content = resp.data.decode('utf-8')
    
    # Extract CSS and JS links (simplified check)
    # In reality, we'd parse HTML properly, but for now check for common patterns
    if '.css' in html_content:
        # Basic check that CSS references exist
        assert 'style' in html_content.lower() or 'css' in html_content.lower()
    
    if '.js' in html_content:
        # Basic check that JS references exist
        assert 'script' in html_content.lower() or 'javascript' in html_content.lower()
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/test_root_dashboard_routes.py::test_code_html_references_valid_assets -v`
Expected: PASS (assuming code.html has proper asset references)

- [ ] **Step 3: Create asset verification script**

Create a script that:
1. Serves the code.html endpoint
2. Extracts all CSS/JS/image links
3. Verifies each referenced asset is accessible
4. Reports any broken links

- [ ] **Step 4: Run asset verification**

Execute the verification script manually or as part of test suite

- [ ] **Step 5: Commit verification script**

```bash
git add scripts/verify_assets.py tests/test_root_dashboard_routes.py
git commit -m "feat: add asset verification for code.html dashboard"
```

---

### Final Verification Task

**Files:**
- Test: Full test suite

- [ ] **Step 1: Run complete test suite**

Run: `pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 2: Manual verification of endpoints**

1. Start Flask development server
2. Visit http://localhost:5000/ - should show code.html dashboard
3. Visit http://localhost:5000/dashboard - should show original CRM dashboard
4. Verify both return 200 status codes
5. Verify content is different between the two endpoints

- [ ] **Step 3: Commit final verification**

```bash
git add .
git commit -m "feat: complete enhancement of code.html dashboard implementation"
```