"""Ports — the behavioural boundary interfaces of the library (hexagonal, private).

In ports-and-adapters terms these ABCs are the **ports**: the abstract operation each
macro-section's concrete classes (the *adapters*) implement. They ship inside the wheel under
``_internal`` but are **not** part of the public API — consumers import the concrete readers,
never these ports. Re-export each port here so callers use one import:
``from opendata_bcb._internal.config.ports import OlindaReaderPort``.
"""

from opendata_bcb._internal.config.ports.olinda_reader_port import OlindaReaderPort


__all__ = [
    "OlindaReaderPort",
]
