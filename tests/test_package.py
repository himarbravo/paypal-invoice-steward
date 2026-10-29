import paypal_invoice_steward


def test_version_is_defined():
    assert isinstance(paypal_invoice_steward.__version__, str)
    assert paypal_invoice_steward.__version__
