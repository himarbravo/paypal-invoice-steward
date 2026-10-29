"""Entry point: `python -m paypal_invoice_steward` or the `paypal-invoice-steward` command."""

from paypal_invoice_steward import __version__


def main() -> None:
    print(f"paypal-invoice-steward {__version__}")


if __name__ == "__main__":
    main()
