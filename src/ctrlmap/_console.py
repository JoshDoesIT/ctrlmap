"""Shared Rich console instance for ctrlmap CLI output.

All CLI commands should import ``console`` from this module rather
than creating ad-hoc ``Console()`` instances at module level.  This
ensures consistent output behavior and makes it easy to redirect or
suppress output during testing.
"""

from rich.console import Console

console = Console()
"""Primary console for user-facing output (writes to stdout)."""

err_console = Console(stderr=True)
"""Console for status/diagnostic messages (writes to stderr)."""
