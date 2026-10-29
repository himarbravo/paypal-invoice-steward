"""Punto de entrada: `python -m paypal_invoice_steward` o el comando `paypal-invoice-steward`."""

from paypal_invoice_steward import __version__


def main() -> None:
    print(f"paypal-invoice-steward {__version__}")


if __name__ == "__main__":
    main()
