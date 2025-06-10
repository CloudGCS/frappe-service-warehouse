import frappe


class ServerBoxService:
    @frappe.whitelist()
    def get_user_boxes():
        """Return all Server Box documents for the tenant of the current user."""
        user = frappe.session.user
        user_doc = frappe.get_doc("User", user)
        # Find the tenant for this user
        tenant = frappe.get_all(
            "Tenant", filters={"user": user_doc.email}, fields=["name"]
        )
        if not tenant:
            frappe.throw("Tenant not found for the user.")
        tenant_name = tenant[0].name
        # Get all Server Boxes for this tenant
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
