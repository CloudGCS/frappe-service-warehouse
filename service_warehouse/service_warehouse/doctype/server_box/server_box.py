# Copyright (c) 2025, CloudGCS and contributors
# For license information, please see license.txt

import frappe
import base64

from frappe.model.document import Document


class ServerBox(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        box_information: DF.JSON | None
        box_ip_address: DF.Data | None
        box_name: DF.Data
        box_type: DF.Literal["Service Box", "Client Box"]
        box_url: DF.Data
        instance_name: DF.Data | None
        name: DF.Int | None
        notes: DF.LongText | None
        server_box_version: DF.Link
        tenant: DF.Link | None
    # end: auto-generated types
    pass

    def validate(self):
        if self.box_type == "Service Box":
            tenant_client_box = frappe.get_all(
                "Server Box",
                filters={"box_type": "Client Box", "tenant": self.tenant},
                fields=["name"],
            )
            if len(tenant_client_box) == 0:
                frappe.throw(
                    "Before creating a Service Box, you must have a Client Box."
                )
        if not self.box_url.startswith("http://") and not self.box_url.startswith(
            "https://"
        ):
            frappe.throw("Box URL must start with 'http://' or 'https://'.")

    def after_insert(self):
        tenant = frappe.get_doc("Tenant", self.tenant)
        box_type = self.box_type.replace(" Box", "")
        instance_name = f"{self.tenant}-{box_type}-{self.name}"
        instance_name = instance_name.lower()
        frappe.db.set_value(
            self.doctype, self.name, "owner", tenant.user, update_modified=False
        )
        frappe.db.set_value(
            self.doctype,
            self.name,
            "instance_name",
            instance_name,
            update_modified=False,
        )
        frappe.db.commit()
        self.reload()


def get_zip_file_content(server_box_id, field_name):
    def get_next_id(current_id):
        result = frappe.db.get_value(
            "Server Box Version",
            filters={"name": [">", current_id]},
            fieldname="name",
            order_by="name ASC",
        )
        return result  # Returns the next higher ID or None if not found

    if not server_box_id:
        frappe.throw("Server Box ID is required to get the zip file.")
    server_box = frappe.get_doc("Server Box", server_box_id)
    if not server_box:
        frappe.throw(f"Server Box with ID {server_box_id} does not exist.")
    if not server_box.server_box_version:
        frappe.throw("Server Box Version is not set for this Server Box.")
    if field_name == "install_zip":
        server_box_version = frappe.get_doc(
            "Server Box Version", server_box.server_box_version
        )
    elif field_name == "update_zip":
        next_server_box_version_id = get_next_id(server_box.server_box_version)
        if not next_server_box_version_id:
            frappe.msgprint("You are using latest Server Box Version. No Update!")
            return None
        server_box_version = frappe.get_doc(
            "Server Box Version", next_server_box_version_id
        )

    file_url = getattr(server_box_version, field_name, None)
    if not file_url:
        frappe.throw(
            f"No file attached in field '{field_name}' for version: {server_box_version.name}"
        )
    file_doc = frappe.get_doc("File", {"file_url": file_url})
    with open(file_doc.get_full_path(), "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    return {"filename": file_doc.file_name, "content_base64": encoded, "success": True}


@frappe.whitelist()
def get_installation_zip(*args, **kwargs):
    try:
        server_box_id = kwargs.get("server_box_id")
        return get_zip_file_content(server_box_id, "install_zip")
    except Exception as e:
        frappe.throw(f"Error while getting installation zip: {str(e)}")


@frappe.whitelist()
def get_update_zip(*args, **kwargs):
    try:
        server_box_id = kwargs.get("server_box_id")
        return get_zip_file_content(server_box_id, "update_zip")
    except Exception as e:
        frappe.throw(f"Error while getting update zip: {str(e)}")


@frappe.whitelist()
def custom_link_query(doctype, txt, searchfield, start, page_len, filters):
    return frappe.db.sql(
        """
        SELECT `name`, `version_name`
        FROM `tabServer Box Version`
        WHERE `version_name` LIKE %s
        ORDER BY `version_name`
        LIMIT %s OFFSET %s
    """,
        ("%%%s%%" % txt, page_len, start),
    )
