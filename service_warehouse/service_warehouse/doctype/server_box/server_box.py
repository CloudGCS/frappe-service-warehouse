# Copyright (c) 2025, CloudGCS and contributors
# For license information, please see license.txt

import re
from urllib.parse import urlparse
import frappe
import base64
import json

from frappe.model.document import Document


class ServerBox(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from service_warehouse.box_setup_settings.doctype.installed_service_packet_version.installed_service_packet_version import InstalledServicePacketVersion

        box_image_information: DF.JSON | None
        box_information: DF.JSON | None
        box_ip_address: DF.Data | None
        box_name: DF.Data
        box_type: DF.Literal["Service Box", "Client Box"]
        box_url: DF.Data
        instance_name: DF.Data | None
        name: DF.Int | None
        notes: DF.LongText | None
        server_box_version: DF.Link
        service_packet_versions: DF.TableMultiSelect[InstalledServicePacketVersion]
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
        if not validate_box_url(self.box_url):
            frappe.throw("Invalid Box URL: It must start with 'http://' or 'https://', and the hostname must only contain letters, numbers, dashes, and dots.")

    def before_save(self):
        box_information = json.loads(self.box_information or "{}")
        installed_service_packet_version_list = []
        if box_information.get("packet_list_info") != None:
            for packet in box_information["packet_list_info"]:
                service_packet_version = frappe.get_all('Service Packet Version', filters={'name': packet["release_version"]})
                if len(service_packet_version) == 0:
                    continue
                installed_service_packet_version = frappe.new_doc('Installed Service Packet Version')
                installed_service_packet_version.service_packet_version = service_packet_version[0].name
                installed_service_packet_version.parent = self.name
                installed_service_packet_version.parenttype = "Server Box"
                installed_service_packet_version.parentfield = "service_packet_versions"
                installed_service_packet_version_list.append(installed_service_packet_version)
        self.service_packet_versions = installed_service_packet_version_list
        if box_information.get("image_versions"):
            self.box_image_information = json.dumps(box_information["image_versions"], indent=4)

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


def validate_box_url(box_url):
    if not (box_url.startswith("http://") or box_url.startswith("https://")):
        return False
    hostname = urlparse(box_url).hostname
    if not hostname or not re.match(r"^[a-zA-Z0-9][-a-zA-Z0-9.]*[a-zA-Z0-9]$", hostname):
        return False
    return True

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
        if field_name == "update_file":
            return {
                "status": False,
                "message": "You are using latest Server Box Version. No Update!",
            }
        else:
            frappe.throw(
                f"No file attached in field '{field_name}' for version: {server_box_version.name}"
            )
    file_doc = frappe.get_doc("File", {"file_url": file_url})
    with open(file_doc.get_full_path(), "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    return {"filename": file_doc.file_name, "content_base64": encoded, "status": True}


@frappe.whitelist()
def get_installation_zip(*args, **kwargs):
    try:
        server_box_id = kwargs.get("server_box_id")
        return get_zip_file_content(server_box_id, "installation_file")
    except Exception as e:
        frappe.throw(f"Error while getting installation zip: {str(e)}")


@frappe.whitelist()
def get_update_zip(*args, **kwargs):
    try:
        server_box_id = kwargs.get("server_box_id")
        return get_zip_file_content(server_box_id, "update_file")
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
