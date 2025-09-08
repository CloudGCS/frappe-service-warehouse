# Copyright (c) 2025, CloudGCS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ServerBoxVersion(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        installation_file: DF.Attach
        name: DF.Int | None
        update_file: DF.Attach | None
        version_name: DF.Data
    # end: auto-generated types
    pass

    def validate(self):
        user = frappe.session.user
        user_data = frappe.get_doc("User", user).as_dict()
        tenant = frappe.get_all(
            "Tenant",
            filters={"user": user_data.get("email")},
            fields=["name"],
        )
        if not tenant or len(tenant) == 0:
            frappe.throw("Tenant not found for the user.")
        tenant_name = tenant[0].name
        if tenant_name != "HOST":
            frappe.throw("Only SYSTEM user can create Server Box Version.")
