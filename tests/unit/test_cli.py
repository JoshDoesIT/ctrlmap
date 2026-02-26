"""Tests for the ctrlmap CLI router."""

from typer.testing import CliRunner

from ctrlmap.cli import app

runner = CliRunner()


class TestCliHelp:
    """Tests for CLI help and version commands."""

    def test_cli_help_returns_zero_exit_code(self) -> None:
        """Running --help should exit cleanly with code 0."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_cli_help_displays_app_name(self) -> None:
        """Help output should mention the app name."""
        result = runner.invoke(app, ["--help"])
        assert "ctrlmap" in result.output.lower() or "privacy" in result.output.lower()

    def test_cli_version_displays_current_version(self) -> None:
        """Running --version should output the version from __init__.py."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_no_args_shows_help(self) -> None:
        """Running ctrlmap with no arguments should show help (no_args_is_help=True)."""
        result = runner.invoke(app, [])
        # Typer/Click exits with code 2 for usage errors (no args provided)
        assert result.exit_code == 2
        assert "Usage" in result.output
