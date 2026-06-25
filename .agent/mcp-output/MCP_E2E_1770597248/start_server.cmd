@echo off
setlocal
cd /d "C:\Users\LifeCycle\Desktop\dekstop projects\gptvli"
set DATABASE_URL=sqlite:///playwright_mcp_MCP_E2E_1770597248.db
set ENABLE_SCHEDULER=0
set ENABLE_CSRF=1
set ADMIN_PASSWORD=admin123
set SESSION_SECRET=mcp-e2e-secret
set LLM_PROVIDER=kie

REM Run server with stdout/stderr redirected to avoid Click/flush issues in hosted shells
python -c "import os; from app import app; app.run(host='127.0.0.1', port=int(os.environ.get('PORT','5000')), debug=False, use_reloader=False)" 1>> ".agent\mcp-output\MCP_E2E_1770597248\server.noreload.log" 2>> ".agent\mcp-output\MCP_E2E_1770597248\server.noreload.err.log"

endlocal
