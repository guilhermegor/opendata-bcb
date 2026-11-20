"""Port every Olinda-backed reader (PTAX, currencies, Focus, ...) implements.

The port pins the one operation a reader exposes — read a reference period into a
provenance-stamped frame — so callers treat any BCB Olinda reader polymorphically. It is
private (``_internal``): consumers import the concrete readers, never this port.
"""

from __future__ import annotations

from abc import abstractmethod
from datetime import date

import pandas as pd

from opendata_bcb._internal.utils.typing import ABCTypeCheckerMeta


class OlindaReaderPort(metaclass=ABCTypeCheckerMeta):
    """Contract for a reader of one Olinda resource.

    Concrete readers inherit the port and its metaclass — do **not** redeclare ``metaclass``.
    """

    @abstractmethod
    def read(self, *, dt_start: date, dt_end: date) -> pd.DataFrame:
        """Return the resource's rows for ``dt_start``..``dt_end`` with provenance columns.

        Parameters
        ----------
        dt_start : datetime.date
            First reference date, inclusive.
        dt_end : datetime.date
            Last reference date, inclusive.

        Returns
        -------
        pd.DataFrame
            The typed, contract-checked, provenance-stamped rows.

        Raises
        ------
        NotImplementedError
            Always — a concrete reader must override this method.
        """
        raise NotImplementedError
