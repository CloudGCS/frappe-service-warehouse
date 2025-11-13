# Copyright (c) 2024, a-techsyn and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ServiceSubscription(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		latest_version: DF.Data | None
		provider: DF.Data | None
		service_packet: DF.Link
		tenant: DF.Link
		title: DF.Data | None
	# end: auto-generated types
	pass
