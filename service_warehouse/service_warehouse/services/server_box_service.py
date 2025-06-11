from logging import exception
import frappe
import json


@frappe.whitelist()
def get_user_boxes():
    user = frappe.session.user
    user_doc = frappe.get_doc("User", user)
    # Find the tenant for this user
    tenant = frappe.get_all("Tenant", filters={"user": user_doc.email}, fields=["name"])
    if not tenant:
        frappe.throw("Tenant not found for the user.")
    tenant_name = tenant[0].name
    boxes = frappe.get_all(
        "Server Box",
        filters={"tenant": tenant_name},
        fields=[
            "box_information",
            "box_ip_address",
            "box_name",
            "box_type",
            "box_url",
            "instance_name",
            "name",
            "notes",
            "server_box_version",
        ],
    )
    return {"boxes": boxes}


@frappe.whitelist()
def update_server_box_info_data(*args, **kwargs):
    try:
        box_info_data_str = kwargs.get("box_info_data")
        if not box_info_data_str:
            frappe.throw("Box information data is required.")
        instance_name = kwargs.get("instance_name")
        if not instance_name:
            frappe.throw("Instance name is required.")
        box_info_data = json.loads(box_info_data_str)
        doc = frappe.get_doc("Server Box", {"instance_name": "instance_name"})
        if not doc:
            frappe.throw(
                f"Server Box with instance name {instance_name} does not exist."
            )
        doc.box_information = box_info_data
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return {"message": "Server box info data updated successfully."}
    except exception as e:
        frappe.throw(f"Error occured while updating server box info data: {str(e)}")
