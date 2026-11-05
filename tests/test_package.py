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


@pytest.mark.parametrize(
    "host", ["0.0.0.0", "192.168.1.12", "steward.example", "127.0.0.2", ""]
)
def test_server_refuses_non_loopback_bindings(
    monkeypatch: "pytest.MonkeyPatch", host: str
) -> None:
    from paypal_invoice_steward.__main__ import main

    monkeypatch.setattr("sys.argv", ["paypal-invoice-steward"])
    monkeypatch.setenv("HOST", host)
    with pytest.raises(RuntimeError, match="local-only"):
        main()


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_server_allows_loopback_binding(
    monkeypatch: "pytest.MonkeyPatch", host: str
) -> None:
    import uvicorn

    from paypal_invoice_steward.__main__ import main

    arguments: dict[str, object] = {}

    def fake_run(_app: str, **kwargs: object) -> None:
        arguments.update(kwargs)

    monkeypatch.setattr("sys.argv", ["paypal-invoice-steward"])
    monkeypatch.setenv("HOST", host)
    monkeypatch.setattr(uvicorn, "run", fake_run)
    main()
    assert arguments["host"] == host
    assert arguments["factory"] is True
