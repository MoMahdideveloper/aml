# Task Instructions - Code Review Fixes

Please implement the following fixes in the codebase:

1. **Stage Untracked Services**:
   Run `git add services/` to stage the new service files so they are tracked.

2. **Deduplicate `@log_execution` Decorators**:
   - Fix `add_tracer.py` (around line 15) to check if `@log_execution` is already present in the preceding lines before inserting it.
   - Remove all duplicate `@log_execution` decorators across all files in `views/` and `services/` (you can write a quick python script or replace them).

3. **SESSION_SECRET Warning in `app.py`**:
   In `app.py` (around line 139), move the warning check `if not flask_app.debug and flask_app.secret_key == "dev-secret-key-change-in-production":` out of the `@flask_app.before_request` hook (`_check_auth` function) so that it only runs once at startup instead of on every request (it should have 4 spaces of indentation, at the root of `create_app`).

4. **Premature Commit in `services/database_service.py`**:
   In `services/database_service.py` (around line 874), remove `db.session.commit()` and `db.session.rollback()` from the `add_ai_history` method so it doesn't prematurely commit transactions managed by outer functions (like `create_property_with_validation`).

5. **Type Casting in Property Rollback**:
   In `views/properties.py` (around line 142), in the `rollback_property_field` function, replace `type(current_value)` with `Property.__table__.columns[field_name].type.python_type` to avoid writing string values into integer/float DB columns when the current value is `None`.

6. **Resource Leaks in Report Generation**:
   In `views/main.py` (around line 1500):
   - In `_generate_pdf_report` and `_generate_excel_report`, use `io.BytesIO` as the destination buffer instead of `tempfile.NamedTemporaryFile(delete=False)` to prevent disk file leaks.
   - In `_generate_json_report`, return the JSON response directly using `jsonify(export_data)` or a custom Response object.

7. **Deprecated `.query.get()`**:
   In `views/properties.py` (around line 124) and other files, replace deprecated `Property.query.get(id)` with `db.session.get(Property, id)`.

Once you have completed these changes, run the pytest suite (`python -m pytest -q`) to verify they are correct and pass.
After verification, you can delete this `task_instructions.md` file.
