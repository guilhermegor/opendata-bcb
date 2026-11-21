"""opendata-bcb package."""

from importlib.metadata import PackageNotFoundError, version

from .banks import read_banks
from .currency_codes import read_currency_codes
from .focus import read_focus_annual_expectations
from .main import main
from .ptax import read_ptax_currencies, read_ptax_quotes, read_ptax_usd_brl
from .quote_bulletins import read_quote_bulletin_codes, read_quote_bulletins
from .sgs import read_sgs_metadata, read_sgs_series


try:
    __version__ = version("opendata-bcb")
except PackageNotFoundError:  # pragma: no cover - source tree without an installed dist
    __version__ = "0.0.0"


__all__ = [
    "__version__",
    "main",
    "read_banks",
    "read_currency_codes",
    "read_focus_annual_expectations",
    "read_ptax_currencies",
    "read_ptax_quotes",
    "read_ptax_usd_brl",
    "read_quote_bulletin_codes",
    "read_quote_bulletins",
    "read_sgs_metadata",
    "read_sgs_series",
]
