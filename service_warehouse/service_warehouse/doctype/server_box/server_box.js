// Copyright (c) 2025, CloudGCS and contributors
// For license information, please see license.txt

frappe.ui.form.on("Server Box", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button("Get Update Zip", function () {
				get_zip_content(frm, "get_update_zip");
			});
			change_fields_read_only_property(frm, 1);
			if (frappe.user_roles.includes("Host")) {
				frm.add_custom_button("Get Installation Zip", function () {
					get_zip_content(frm, "get_installation_zip");
				});
				frm.set_df_property("instance_name", "read_only", 0);
			}
		} else {
			change_fields_read_only_property(frm, 0);
		}
	},
	onload: function (frm) {
		frm.set_query("server_box_version", () => {
			return {
				query: "service_warehouse.service_warehouse.doctype.server_box.server_box.custom_link_query",
			};
		});
	},
});

function get_zip_content(frm, command) {
	frappe.call({
		method: `service_warehouse.service_warehouse.doctype.server_box.server_box.${command}`,
		args: { server_box_id: frm.doc.name },
		callback: (r) => {
			if (r.message && r.message.status) {
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
			} else {
				frappe.msgprint(r.message.message || "Failed to get the zip file.");
			}
		},
	});
}

function change_fields_read_only_property(frm, read_only) {
	frm.set_df_property("box_type", "read_only", read_only);
	frm.set_df_property("server_box_version", "read_only", read_only);
	frm.set_df_property("box_url", "read_only", read_only);
	frm.set_df_property("tenant", "read_only", read_only);
}
