"""ctrlmap: Privacy-preserving GRC automation CLI."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__: str = version("ctrlmap")
except PackageNotFoundError:  # pragma: no cover - editable/dev installs
    __version__ = "0.0.0-dev"
