// Copyright (c) 2024, a-techsyn and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Extension", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.owner && frm.doc.owner !== frappe.session.user) {
			frm.page.remove_menu_item(__("Duplicate"));
		}
	},
});
