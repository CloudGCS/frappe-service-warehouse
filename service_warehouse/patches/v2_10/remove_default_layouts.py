import frappe


def execute():
	if frappe.db.table_exists("Default Layouts"):
		frappe.db.delete("Default Layouts")
		frappe.db.commit()

	if frappe.db.exists("DocType", "Default Layouts"):
		frappe.delete_doc("DocType", "Default Layouts", force=True, ignore_permissions=True)
		frappe.db.commit()
