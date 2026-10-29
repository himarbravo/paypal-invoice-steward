"""Paypal Invoice Steward."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("paypal-invoice-steward")
except PackageNotFoundError:  # paquete no instalado (p. ej. ejecutando desde el código fuente)
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
