# Copyright (c) 2026, CloudGCS and contributors
# For license information, please see license.txt

# import frappe
from typing import TYPE_CHECKING

from frappe.model.document import Document

if TYPE_CHECKING:
	from frappe.types import DF


class PilotFlightLog(Document):
	if TYPE_CHECKING:
		aircraft_name: DF.Data | None
		flight_date: DF.Date | None
		flight_hours: DF.Float
		pilot: DF.Link
		source_flight_id: DF.Data | None
		tenant: DF.Link
		tenant_name: DF.Data | None
	pass
