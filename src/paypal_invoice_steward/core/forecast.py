"""Cash-flow forecast: when will the money on open invoices actually arrive?

Each customer pays with their own habit, measured as days after the due date.
Habits are estimated from paid invoices and shrunk toward the overall average
when a customer has little history. Open invoices are then simulated many times
to get an expected weekly inflow with a p10 to p90 range, instead of a single
number that pretends to be certain.

An overdue invoice is conditioned on what we already know: it has not been paid
yet, so its simulated payment date can never be earlier than today.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from datetime import date, timedelta

from .models import JSON, Invoice

HORIZON_WEEKS = 8
SHRINKAGE = 3  # a customer with 3 paid invoices counts as half their own history
MIN_SD = 3.0
DEFAULT_MEAN, DEFAULT_SD = 7.0, 10.0
BASE_DEFAULT_RATE = 0.03  # chance an invoice is never collected
LONG_OVERDUE_DEFAULT_RATE = 0.15  # same, once it is more than 60 days late
BEYOND_HABIT_Z = 1.5  # "much later than this customer usually pays"
BEYOND_HABIT_EXTRA_DEFAULT = 0.10  # extra chance of never collecting in that case


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _var(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return sum((v - m) ** 2 for v in values) / (len(values) - 1)


Habits = dict[str, tuple[float, float, int]]
"""Per customer: (mean delay in days, standard deviation, number of paid invoices)."""


def payment_habits(invoices: list[Invoice]) -> tuple[Habits, tuple[float, float]]:
    """Return ({customer: (mean_delay, sd_delay, n_paid)}, (global_mean, global_sd))."""
    delays: dict[str, list[float]] = defaultdict(list)
    for inv in invoices:
        if inv.status == "paid" and inv.paid is not None:
            delays[inv.customer_name].append(float((inv.paid - inv.due).days))
    everything = [d for values in delays.values() for d in values]
    if everything:
        g_mean, g_sd = _mean(everything), max(math.sqrt(_var(everything)), MIN_SD)
    else:
        g_mean, g_sd = DEFAULT_MEAN, DEFAULT_SD

    habits: Habits = {}
    for name, values in delays.items():
        n = len(values)
        w = n / (n + SHRINKAGE)
        mean = w * _mean(values) + (1 - w) * g_mean
        var = w * _var(values) + (1 - w) * g_sd**2
        habits[name] = (mean, max(math.sqrt(var), MIN_SD), n)
    return habits, (g_mean, g_sd)


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(int(q * (len(sorted_values) - 1) + 0.5), len(sorted_values) - 1)
    return sorted_values[idx]


def _tail_wait(rng: random.Random, overdue: int) -> float:
    """Wait for an invoice that is already far later than its customer's habit.

    The habit no longer explains it, so use the "longer unpaid, longer to wait"
    rule: exponential with a scale of half the days already overdue (at least 14).
    """
    return rng.expovariate(1.0 / max(0.5 * overdue, 14.0))


def _simulate_payment_day(
    rng: random.Random, inv: Invoice, mean: float, sd: float, today: date
) -> float | None:
    """Days from today until payment, or None if the invoice is never collected."""
    overdue = max((today - inv.due).days, 0)
    beyond_habit = overdue > 0 and (overdue - mean) / sd > BEYOND_HABIT_Z
    p_default = LONG_OVERDUE_DEFAULT_RATE if overdue > 60 else BASE_DEFAULT_RATE
    if beyond_habit:
        p_default += BEYOND_HABIT_EXTRA_DEFAULT
    if rng.random() < p_default:
        return None
    if beyond_habit:
        return _tail_wait(rng, overdue)
    due_in = (inv.due - today).days
    for _ in range(60):
        pay_in = due_in + rng.gauss(mean, sd)
        if pay_in >= 0:
            return pay_in
    return _tail_wait(rng, overdue)  # habit says it should be paid by now, yet it is not


def forecast(
    invoices: list[Invoice],
    today: date,
    horizon_weeks: int = HORIZON_WEEKS,
    sims: int = 2000,
    seed: int = 7,
) -> dict[str, JSON]:
    """Forecast per currency. Returns {currency: result}."""
    habits, (g_mean, g_sd) = payment_habits(invoices)
    open_invoices = [i for i in invoices if i.status == "open"]
    by_currency: dict[str, list[Invoice]] = defaultdict(list)
    for inv in open_invoices:
        by_currency[inv.currency].append(inv)

    results: dict[str, JSON] = {}
    for currency, group in by_currency.items():
        rng = random.Random(f"{seed}:{currency}")
        week_totals = [[0.0] * sims for _ in range(horizon_weeks)]
        later_totals = [0.0] * sims
        per_invoice: dict[str, list[float | None]] = {}

        for inv in group:
            mean, sd, _ = habits.get(inv.customer_name, (g_mean, g_sd, 0))
            outcomes: list[float | None] = []
            for s in range(sims):
                pay_in = _simulate_payment_day(rng, inv, mean, sd, today)
                outcomes.append(pay_in)
                if pay_in is None:
                    continue
                week = int(pay_in // 7)
                if week < horizon_weeks:
                    week_totals[week][s] += inv.amount
                else:
                    later_totals[s] += inv.amount
            per_invoice[inv.id] = outcomes

        weeks: list[JSON] = []
        for w in range(horizon_weeks):
            ordered = sorted(week_totals[w])
            start = today + timedelta(days=7 * w)
            weeks.append(
                {
                    "start": start.isoformat(),
                    "end": (start + timedelta(days=6)).isoformat(),
                    "expected": round(_mean(week_totals[w]), 2),
                    "p10": round(_quantile(ordered, 0.10), 2),
                    "p90": round(_quantile(ordered, 0.90), 2),
                }
            )
        in_horizon = [sum(week_totals[w][s] for w in range(horizon_weeks)) for s in range(sims)]
        ordered_total = sorted(in_horizon)

        rows: list[JSON] = []
        for inv in group:
            outcomes = per_invoice[inv.id]
            paid_30 = sum(1 for o in outcomes if o is not None and o <= 30) / sims
            landed = sorted(o for o in outcomes if o is not None)
            median_day = _quantile(landed, 0.5) if landed else None
            median_date = (
                (today + timedelta(days=round(median_day))).isoformat()
                if median_day is not None
                else None
            )
            risk = "high" if paid_30 < 0.5 else "medium" if paid_30 < 0.8 else "low"
            rows.append(
                {
                    "id": inv.id,
                    "number": inv.number,
                    "customer": inv.customer_name,
                    "amount": inv.amount,
                    "due": inv.due.isoformat(),
                    "days_overdue": inv.days_overdue(today),
                    "p_paid_30d": round(paid_30, 3),
                    "median_pay_date": median_date,
                    "risk": risk,
                }
            )
        rows.sort(key=lambda r: (-{"high": 2, "medium": 1, "low": 0}[r["risk"]], -r["amount"]))

        open_amount = round(sum(i.amount for i in group), 2)
        results[currency] = {
            "currency": currency,
            "as_of": today.isoformat(),
            "open_amount": open_amount,
            "at_risk_amount": round(sum(r["amount"] for r in rows if r["risk"] == "high"), 2),
            "total": {
                "expected": round(_mean(in_horizon), 2),
                "p10": round(_quantile(ordered_total, 0.10), 2),
                "p90": round(_quantile(ordered_total, 0.90), 2),
            },
            "later_or_never_expected": round(_mean(later_totals), 2),
            "weeks": weeks,
            "invoices": rows,
            "customers": [
                {
                    "name": name,
                    "avg_delay_days": round(m, 1),
                    "sd_days": round(sd, 1),
                    "paid_invoices": n,
                }
                for name, (m, sd, n) in sorted(habits.items(), key=lambda kv: -kv[1][0])
            ],
            "method": (
                f"{sims} Monte Carlo runs. Each customer's payment delay after the due date "
                "is estimated from their paid invoices (shrunk toward the average when history "
                "is short). "
                "An invoice already much later than its customer's habit is treated as "
                "unusual: it is expected to take longer the longer it has been unpaid, and the "
                "chance it is never collected goes up."
            ),
        }
    return results
