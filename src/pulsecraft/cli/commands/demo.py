"""demo command — start the PulseCraft demo web UI."""

from __future__ import annotations

import typer

app = typer.Typer(name="demo", help="Demo web UI commands.", no_args_is_help=True)


def register(parent: typer.Typer) -> None:
    parent.add_typer(app, name="demo")


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to."),  # noqa: B008
    port: int = typer.Option(8000, "--port", help="Port to bind to."),  # noqa: B008
    open_browser: bool = typer.Option(  # noqa: B008
        False, "--open-browser", help="Open browser after server starts."
    ),
    log_level: str = typer.Option("warning", "--log-level", help="uvicorn log level."),  # noqa: B008
) -> None:
    """Start the PulseCraft demo server at http://HOST:PORT.

    Serves a polished single-page UI that runs real pipeline scenarios and
    streams decisions live as they happen. Built for Head of AI demo.

    Example:
      pulsecraft demo serve
      pulsecraft demo serve --port 9000 --open-browser
    """
    import uvicorn

    typer.echo(f"Starting PulseCraft demo at http://{host}:{port}")
    typer.echo("Press Ctrl+C to stop.\n")

    if open_browser:
        import threading
        import time
        import webbrowser

        def _open() -> None:
            time.sleep(1.2)
            webbrowser.open(f"http://{host}:{port}")

        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(
        "pulsecraft.demo.server:app",
        host=host,
        port=port,
        log_level=log_level,
    )
