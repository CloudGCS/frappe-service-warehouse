// Copyright (c) 2025, CloudGCS and contributors
// For license information, please see license.txt

frappe.ui.form.on("Server Box", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button("Get Installation Zip", function () {
				get_zip_content(frm, "get_installation_zip");
			});
			frm.add_custom_button("Get Update Zip", function () {
				get_zip_content(frm, "get_update_zip");
			});
			frm.set_df_property("server_box_version", "read_only", 1);
		}
	},
});

function get_zip_content(frm, command) {
	frappe.call({
		method: `service_warehouse.service_warehouse.doctype.server_box.server_box.${command}`,
		args: { server_box_id: frm.doc.name },
		callback: (r) => {
			if (r.message) {
				const base64Data = r.message.content_base64;
				const byteCharacters = atob(base64Data);
				const byteNumbers = new Array(byteCharacters.length);
				for (let i = 0; i < byteCharacters.length; i++) {
					byteNumbers[i] = byteCharacters.charCodeAt(i);
				}
				const byteArray = new Uint8Array(byteNumbers);
				const blob = new Blob([byteArray], { type: "application/zip" });
				// Create a link and trigger download
				const link = document.createElement("a");
				link.href = window.URL.createObjectURL(blob);
				link.download = `${r.message.filename}`;
				document.body.appendChild(link);
				link.click();
				document.body.removeChild(link);
				frm.reload_doc();
			}
		},
	});
}
