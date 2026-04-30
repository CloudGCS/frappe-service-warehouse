# Copyright (c) 2026, CloudGCS and contributors
# For license information, please see license.txt

import frappe
from typing import TYPE_CHECKING

from frappe.model.document import Document

if TYPE_CHECKING:
        from frappe.types import DF
        from service_warehouse.service_warehouse.doctype.pilot_certificate.pilot_certificate import PilotCertificate
        from service_warehouse.pilot_marketplace.doctype.pilot_flight_experience.pilot_flight_experience import (
            PilotFlightExperience,
        )


class PilotProfile(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from service_warehouse.service_warehouse.doctype.pilot_certificate.pilot_certificate import PilotCertificate
        from service_warehouse.pilot_marketplace.doctype.pilot_flight_experience.pilot_flight_experience import PilotFlightExperience

        certificates: DF.Table[PilotCertificate]
        email: DF.Data | None
        flight_experiences: DF.Table[PilotFlightExperience]
        full_name: DF.Data | None
        phone: DF.Data | None
        pilot_id: DF.Data | None
        status: DF.Literal["Active", "Inactive", "Pending"]
        time_zone: DF.Autocomplete | None
        total_flight_hours: DF.Float
        user: DF.Link
    # end: auto-generated types

    def onload(self):
        total = frappe.db.get_value(
            "Pilot Flight",
            filters={"pilot": self.name},
            fieldname="sum(flight_hours)",
            as_dict=False,
        ) or 0
        total_hours = float(total) / 3600 if total else 0
        self.set_onload("total_flight_hours", total_hours)
        self.total_flight_hours = total_hours

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

        if self.is_new() and not self.phone:
            self.phone = self._get_user_phone()

        if self.is_new() and not self.time_zone:
            self.time_zone = self._get_user_time_zone()

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
