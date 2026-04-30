# Copyright (c) 2026, CloudGCS and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING

from frappe.model.document import Document

if TYPE_CHECKING:
	from frappe.types import DF


class PilotFlightExperience(Document):
	if TYPE_CHECKING:
		aircraft_type: DF.Data
		flight_hours: DF.Float | None
		location: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	pass
