import frappe
import json


@frappe.whitelist()
def get_user_boxes():
    user = frappe.session.user
    user_doc = frappe.get_doc("User", user)
    # Find the tenant for this user
    boxes = frappe.get_all(
        "Server Box",
        filters={"owner": user_doc.name},
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
        box_info_data = kwargs.get("box_info_data")
        if not box_info_data:
            frappe.throw("Box information data is required.")
        instance_name = kwargs.get("instance_name")
        # server_box_version = kwargs.get("server_box_version")
        if not instance_name:
            frappe.throw("Instance name is required.")
        doc = frappe.get_doc("Server Box", {"instance_name": instance_name})
        if not doc:
            frappe.throw(
                f"Server Box with instance name {instance_name} does not exist."
            )
        frappe.db.set_value(
            doc.doctype, doc.name, "box_information", json.dumps(box_info_data, indent=2)
        )
        # frappe.db.set_value(
        #     doc.doctype, doc.name, "server_box_version", server_box_version
        # )
        frappe.db.commit()
        return {"message": "Server box info data updated successfully."}
    except Exception as e:
        frappe.throw(f"Error occured while updating server box info data: {str(e)}")
