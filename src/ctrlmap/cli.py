"""ctrlmap CLI — Typer command routing and argument parsing."""

import typer

from ctrlmap import __version__

app = typer.Typer(
    name="ctrlmap",
    help="Privacy-preserving GRC automation CLI. Map policies to security frameworks locally.",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Print the version and exit."""
    if value:
        typer.echo(f"ctrlmap {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show the version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Privacy-preserving GRC automation CLI."""
