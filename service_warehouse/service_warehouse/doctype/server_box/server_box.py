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
            user = frappe.session.user
            user_data = frappe.get_doc("User", user).as_dict()
            tenant_client_box = frappe.get_all(
                "Server Box",
                filters={
                    "box_type": "Client Box",
                    "owner": user_data.get("name"),
                },
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
        user = frappe.session.user
        user_data = frappe.get_doc("User", user).as_dict()
        tenant = frappe.get_all("Tenant", filters={"user": user_data.get("email")})
        if not tenant or len(tenant) == 0:
            frappe.throw("Tenant not found for the user.")
        tenant_name = tenant[0].name
        box_type = self.box_type.replace(" Box", "")
        instance_name = f"{tenant_name}-{box_type}-{self.name}"
        self.instance_name = instance_name.lower()
        self.save()
        self.reload()


def get_zip_file_content(server_box_id, field_name):
    if not server_box_id:
        frappe.throw("Server Box ID is required to get the zip file.")
    server_box = frappe.get_doc("Server Box", server_box_id)
    if not server_box:
        frappe.throw(f"Server Box with ID {server_box_id} does not exist.")
    if not server_box.server_box_version:
        frappe.throw("Server Box Version is not set for this Server Box.")
    server_box_version = frappe.get_doc(
        "Server Box Version", server_box.server_box_version
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


def getNextBoxVersion(server_box_id):
    server_box = frappe.get_doc("Server Box", server_box_id)
    if not server_box:
        frappe.throw(f"Server Box with ID {server_box_id} does not exist.")
    server_box_versions = frappe.get_all("Server Box Version")
    server_box_versions.sort(key=lambda x: x.name, reverse=True)
    for version in server_box_versions:
        if int(version.name) > int(server_box.server_box_version):
            server_box_version = frappe.get_doc("Server Box Version", version)
            return server_box_version
    return None


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
        new_version = getNextBoxVersion(server_box_id)
        if new_version is not None:
            server_box = frappe.get_doc("Server Box", server_box_id)
            if not server_box:
                frappe.throw(f"Server Box with ID {server_box_id} does not exist.")
            if not new_version.update_zip:
                frappe.throw(
                    f"No update zip file found for version: {new_version.name}"
                )
            frappe.db.set_value(
                "Server Box", server_box.name, "server_box_version", new_version.name
            )
            frappe.db.commit()
            return get_zip_file_content(server_box_id, "update_zip")

        frappe.msgprint(
            msg="You are using latest box version.",
            title="Box Update Message!",
            raise_exception=False,
            indicator="yellow",
        )
    except Exception as e:
        frappe.throw(f"Error while getting update zip: {str(e)}")
