# Copyright (c) 2026, CloudGCS and contributors
# For license information, please see license.txt

# import frappe
from typing import TYPE_CHECKING

from frappe.model.document import Document

if TYPE_CHECKING:
	from frappe.types import DF


class PilotCertificate(Document):
	if TYPE_CHECKING:
		certificate_file: DF.Attach | None
		certificate_name: DF.Data
		expiry_date: DF.Date | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	pass
