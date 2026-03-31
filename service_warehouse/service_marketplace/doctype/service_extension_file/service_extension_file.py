# Copyright (c) 2026, CloudGCS and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ServiceExtensionFile(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		se_file: DF.Attach
	# end: auto-generated types
	pass
