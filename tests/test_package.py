import pytest

import paypal_invoice_steward


def test_version_is_defined():
    assert isinstance(paypal_invoice_steward.__version__, str)
    assert paypal_invoice_steward.__version__


def test_version_flag_prints_and_exits(
    capsys: "pytest.CaptureFixture[str]", monkeypatch: "pytest.MonkeyPatch"
) -> None:
    from paypal_invoice_steward.__main__ import main

    monkeypatch.setattr("sys.argv", ["paypal-invoice-steward", "--version"])
    main()
    assert capsys.readouterr().out.startswith("paypal-invoice-steward ")
