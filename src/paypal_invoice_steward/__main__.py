"""Entry point: `python -m paypal_invoice_steward` or the `paypal-invoice-steward` command.

Starts the web app on http://127.0.0.1:8000 (`HOST` and `PORT` override it).
`--version` prints the version and exits.
"""

import os
import sys

from paypal_invoice_steward import __version__


def main() -> None:
    if "--version" in sys.argv[1:]:
        print(f"paypal-invoice-steward {__version__}")
        return
    import uvicorn

    uvicorn.run(
        "paypal_invoice_steward.ui.web:create_app",
        factory=True,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
    )


if __name__ == "__main__":
    main()
