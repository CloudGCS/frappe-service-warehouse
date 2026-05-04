# Copyright (c) 2026, CloudGCS and contributors
# For license information, please see license.txt

import frappe
from typing import TYPE_CHECKING

from frappe.model.document import Document
from frappe.utils import cint, duration_to_seconds, flt

SECONDS_PER_HOUR = 3600

if TYPE_CHECKING:
    from collections.abc import Iterable

    from frappe.model.base_document import BaseDocument
    from frappe.types import DF
    from service_warehouse.service_warehouse.doctype.pilot_certificate.pilot_certificate import PilotCertificate
    from service_warehouse.pilot_marketplace.doctype.pilot_flight_experience.pilot_flight_experience import (
        PilotFlightExperience,
    )

    ChildRow = BaseDocument | dict[str, object]


def _duration_value_to_seconds(value, *, numeric_unit: str = "seconds") -> int:
    if value in (None, ""):
        return 0

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0

        if any(token in value.lower() for token in ("d", "h", "m", "s")):
            return duration_to_seconds(value)

    multiplier = SECONDS_PER_HOUR if numeric_unit == "hours" else 1
    return cint(round(flt(value) * multiplier))


def get_total_flight_hours_seconds(
    profile_name: str | None, flight_experiences: "Iterable[ChildRow] | None" = None
) -> int:
    total_seconds = 0

    if profile_name:
        total_seconds += cint(
            round(
                flt(
                    frappe.db.get_value(
                        "Pilot Flight",
                        filters={"pilot": profile_name},
                        fieldname="sum(flight_hours)",
                        as_dict=False,
                    )
                    or 0
                )
            )
        )

    if flight_experiences is None and profile_name:
        flight_experiences = frappe.get_all(
            "Pilot Flight Experience",
            filters={"parent": profile_name, "parenttype": "Pilot Profile", "parentfield": "flight_experiences"},
            fields=["flight_hours"],
        )

    for row in flight_experiences or []:
        hours = row.get("flight_hours") if isinstance(row, dict) else row.flight_hours
        total_seconds += _duration_value_to_seconds(hours, numeric_unit="hours")

    return total_seconds


def sync_total_flight_hours(profile_name: str | None, *, update_modified: bool = False) -> int:
    if not profile_name or not frappe.db.exists("Pilot Profile", profile_name):
        return 0

    total_seconds = get_total_flight_hours_seconds(profile_name)
    frappe.db.set_value(
        "Pilot Profile",
        profile_name,
        "total_flight_hours",
        total_seconds,
        update_modified=update_modified,
    )
    return total_seconds


class PilotProfile(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from service_warehouse.pilot_marketplace.doctype.pilot_flight_experience.pilot_flight_experience import PilotFlightExperience
        from service_warehouse.service_warehouse.doctype.pilot_certificate.pilot_certificate import PilotCertificate

        certificates: DF.Table[PilotCertificate]
        email: DF.Data | None
        flight_experiences: DF.Table[PilotFlightExperience]
        full_name: DF.Data | None
        phone: DF.Data | None
        pilot_id: DF.Data | None
        status: DF.Literal["Active", "Inactive", "Pending"]
        time_zone: DF.Autocomplete | None
        total_flight_hours: DF.Duration | None
        user: DF.Link
    # end: auto-generated types

    def onload(self):
        self.total_flight_hours = get_total_flight_hours_seconds(self.name)

        user_phone = self._get_user_phone()
        if self.phone != user_phone:
            self.phone = user_phone

        user_time_zone = self._get_user_time_zone()
        if self.time_zone != user_time_zone:
            self.time_zone = user_time_zone

    def validate(self):
        if self.user:
            self.owner = self.user

        self.phone = self._normalize_phone(self.phone)
        self.time_zone = self._normalize_time_zone(self.time_zone)
        self._normalize_flight_experience_hours()

        if self.is_new() and not self.phone:
            self.phone = self._get_user_phone()

        if self.is_new() and not self.time_zone:
            self.time_zone = self._get_user_time_zone()

        self.total_flight_hours = get_total_flight_hours_seconds(
            self.name,
            flight_experiences=self.flight_experiences,
        )

    def on_update(self):
        if not self.user:
            return

        user_phone = self._get_user_phone()
        if user_phone != self.phone:
            frappe.db.set_value("User", self.user, "phone", self.phone, update_modified=False)

        user_time_zone = self._get_user_time_zone()
        if user_time_zone != self.time_zone:
            frappe.db.set_value("User", self.user, "time_zone", self.time_zone, update_modified=False)

    def _get_user_phone(self):
        if not self.user:
            return None

        return self._normalize_phone(frappe.db.get_value("User", self.user, "phone"))

    def _get_user_time_zone(self):
        if not self.user:
            return None

        return self._normalize_time_zone(frappe.db.get_value("User", self.user, "time_zone"))

    def _normalize_flight_experience_hours(self):
        for row in self.flight_experiences or []:
            if row.flight_hours is not None:
                row.flight_hours = flt(row.flight_hours, 2)

    @staticmethod
    def _normalize_phone(value):
        if not isinstance(value, str):
            return value

        value = value.strip()
        return value or None

    @staticmethod
    def _normalize_time_zone(value):
        if not isinstance(value, str):
            return value

        value = value.strip()
        return value or None


def has_permission(doc, ptype="read", user=None, debug=False):
    user = user or frappe.session.user

    if ptype in ("write", "delete", "amend", "cancel"):
        return user == doc.user or "Host" in frappe.get_roles(user)

    return None


@frappe.whitelist()
def backfill_pilot_profile_owners():
    frappe.only_for("System Manager")

    profiles = frappe.get_all("Pilot Profile", fields=["name", "user", "owner"])
    updated_count = 0

    for profile in profiles:
        if profile.user and profile.owner != profile.user:
            frappe.db.set_value("Pilot Profile", profile.name, "owner", profile.user, update_modified=False)
            updated_count += 1

    if updated_count:
        frappe.db.commit()

    return {"updated_count": updated_count}
