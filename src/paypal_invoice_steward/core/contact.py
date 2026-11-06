"""Operator-only local contact controls; no external dispute adjudication or settings writes."""

import re

from .models import JSON
from .ports import ProposalStore
from .proposals import Conflict, PolicyError

HOLD_REASONS = {"dispute", "complaint", "contact_preference", "other_review"}
HOLD_NOTICE = (
    "A local hold cannot recall an in-flight request or stop PayPal automatic reminders "
    "or other contact. The operator must review external schedules with the account owner."
)


class ContactService:
    def __init__(self, store: ProposalStore) -> None:
        self.store = store

    def change(
        self, invoice_id: str, reason: str | None, expected_version: str | None = None
    ) -> JSON:
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", invoice_id) is None:
            raise PolicyError("Invalid invoice identifier.")
        if reason is not None and reason not in HOLD_REASONS:
            raise PolicyError("Choose a supported contact hold reason.")
        hold = self.store.change_contact_hold(invoice_id, reason, expected_version)
        if hold is None:
            raise Conflict("Contact hold changed. Reload and review it before releasing.")
        return {"hold": hold, "notice": HOLD_NOTICE}
