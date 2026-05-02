"""Run the API with Uvicorn: ``python -m search_agent`` from the ``backend`` folder (venv on PATH, package installed editable)."""

from __future__ import annotations

from pathlib import Path

import uvicorn


def main() -> None:
    src = Path(__file__).resolve().parent.parent
    uvicorn.run(
        "search_agent.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        app_dir=str(src),
    )


if __name__ == "__main__":
    main()
