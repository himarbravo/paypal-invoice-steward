from datetime import date, timedelta

from paypal_invoice_steward.core.forecast import forecast, payment_habits
from paypal_invoice_steward.core.models import Invoice

TODAY = date(2026, 10, 29)


def _open(i: int, name: str, amount: float, due_offset: int) -> Invoice:
    return Invoice(
        id=f"o{i}",
        number=f"N{i}",
        customer_name=name,
        customer_email="a@b.co",
        amount=amount,
        currency="EUR",
        status="open",
        issued=TODAY - timedelta(days=30),
        due=TODAY + timedelta(days=due_offset),
    )


def _paid(i: int, name: str, delay: int) -> Invoice:
    due = TODAY - timedelta(days=60)
    return Invoice(
        id=f"p{i}",
        number=f"P{i}",
        customer_name=name,
        customer_email="a@b.co",
        amount=100,
        currency="EUR",
        status="paid",
        issued=due - timedelta(days=14),
        due=due,
        paid=due + timedelta(days=delay),
    )


def _book() -> list[Invoice]:
    history = [_paid(i, "Fast", 1) for i in range(4)] + [
        _paid(10 + i, "Slow", 30) for i in range(4)
    ]
    return history + [
        _open(1, "Fast", 1200, 5),
        _open(2, "Slow", 800, -10),
        _open(3, "New", 500, 20),
    ]


def test_weeks_have_sane_ranges() -> None:
    data = forecast(_book(), TODAY)["EUR"]
    assert data["open_amount"] == 2500
    assert 0 <= data["at_risk_amount"] <= data["open_amount"]
    assert len(data["weeks"]) == 8
    for week in data["weeks"]:
        assert 0 <= week["p10"] <= week["p90"]


def test_forecast_is_deterministic() -> None:
    assert forecast(_book(), TODAY) == forecast(_book(), TODAY)


def test_expected_inflow_never_exceeds_what_is_owed() -> None:
    data = forecast(_book(), TODAY)["EUR"]
    assert sum(w["expected"] for w in data["weeks"]) <= data["open_amount"] + 1


def test_slow_payer_is_riskier_than_fast_payer() -> None:
    history = [_paid(i, "Fast", 0) for i in range(4)] + [
        _paid(10 + i, "Slow", 45) for i in range(4)
    ]
    invoices = [*history, _open(1, "Fast", 1000, 5), _open(2, "Slow", 1000, 5)]
    rows = {r["id"]: r for r in forecast(invoices, TODAY)["EUR"]["invoices"]}
    assert rows["o1"]["p_paid_30d"] > rows["o2"]["p_paid_30d"]


def test_very_late_invoice_is_not_overconfident() -> None:
    invoices = [*(_paid(i, "Usual", 5) for i in range(5)), _open(1, "Usual", 1000, -80)]
    row = forecast(invoices, TODAY)["EUR"]["invoices"][0]
    assert row["p_paid_30d"] < 0.8
    assert row["risk"] in ("medium", "high")


def test_no_open_invoices_gives_empty_result() -> None:
    assert forecast([_paid(1, "X", 3)], TODAY) == {}


def test_short_history_is_shrunk_toward_the_average() -> None:
    invoices = [_paid(i, "Many", 0) for i in range(10)] + [_paid(20, "Once", 40)]
    habits, (g_mean, _) = payment_habits(invoices)
    once_mean = habits["Once"][0]
    assert g_mean < once_mean < 40


def test_unknown_invoices_are_left_out() -> None:
    weird = _open(9, "Fast", 999, 3)
    weird.status = "unknown"
    data = forecast([*_book(), weird], TODAY)["EUR"]
    assert data["open_amount"] == 2500
