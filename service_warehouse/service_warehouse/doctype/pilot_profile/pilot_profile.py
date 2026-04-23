# Copyright (c) 2026, CloudGCS and contributors
# For license information, please see license.txt

import frappe
from typing import TYPE_CHECKING

from frappe.model.document import Document

if TYPE_CHECKING:
        from frappe.types import DF
        from service_warehouse.service_warehouse.doctype.pilot_certificate.pilot_certificate import PilotCertificate


class PilotProfile(Document):
        if TYPE_CHECKING:
                certificates: DF.Table[PilotCertificate]
                email: DF.Data | None
                full_name: DF.Data | None
                phone: DF.Data | None
                pilot_id: DF.Data | None
                status: DF.Literal["Active", "Inactive", "Pending"]
                total_flight_hours: DF.Float | None
                user: DF.Link

        def onload(self):
                total = frappe.db.get_value(
                        "Pilot Flight Log",
                        filters={"pilot": self.name},
                        fieldname="sum(flight_hours)",
                        as_dict=False,
                ) or 0
                self.set_onload("total_flight_hours", total)
                self.total_flight_hours = total
