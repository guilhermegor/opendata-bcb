"""opendata-bcb package."""

from importlib.metadata import PackageNotFoundError, version

from .ingestion.banks import read_banks
from .ingestion.sgs import read_sgs_series
from .main import main


try:
    __version__ = version("opendata-bcb")
except PackageNotFoundError:  # pragma: no cover - source tree without an installed dist
    __version__ = "0.0.0"


__all__ = [
    "__version__",
    "main",
    "read_banks",
    "read_sgs_series",
]
