import frappe
import json
from service_warehouse.utils.api_utils import APIResponse


@frappe.whitelist()
def get_user_boxes():
    user = frappe.session.user
    boxes = frappe.get_all(
        "Server Box",
        filters={"owner": user},
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
    return APIResponse.success(data={"boxes": boxes})


@frappe.whitelist()
def update_server_box_info_data(*args, **kwargs):
    box_info_data = kwargs.get("box_info_data")
    instance_name = kwargs.get("instance_name")
    server_box_version = kwargs.get("server_box_version")

    if not box_info_data:
        return APIResponse.failed(
            message="Box information data is required.", status_code=400
        )
    if not instance_name:
        return APIResponse.failed(message="Instance name is required.", status_code=400)
    if not frappe.db.exists("Server Box", {"instance_name": instance_name}):
        return APIResponse.failed(
            message=f"Server Box with instance name {instance_name} does not exist.",
            status_code=404,
        )

    try:
        doc = frappe.get_doc("Server Box", {"instance_name": instance_name})
        doc.box_information = json.dumps(box_info_data, indent=2)
        server_box_version_doc = frappe.get_doc(
            "Server Box Version", {"version_name": server_box_version}
        )
        doc.server_box_version = server_box_version_doc
        doc.save()
        frappe.db.commit()
        return APIResponse.success(message="Server box info data updated successfully.")

    except frappe.ValidationError as e:
        return APIResponse.failed(message=str(e), status_code=400)
    except Exception as e:
        frappe.log_error(message=str(e), title="update_server_box_info_data failed")
        return APIResponse.failed(
            message=f"Unexpected error occurred: {str(e)}", status_code=500
        )
