import os

from app import app


if __name__ == "__main__":
    # Stable dev server for Playwright MCP verification.
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "5000")),
        debug=False,
        use_reloader=False,
    )
