// Copyright (c) 2024, a-techsyn and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Packet Version", {
  refresh: async function(frm) {
		if (!frm.is_new() && frm.doc.owner && frm.doc.owner !== frappe.session.user) {
			frm.page.menu
				.find(".menu-item-label")
				.filter(function () { return $(this).text().trim() === __("Duplicate"); })
				.closest("li")
				.addClass("hide");
		}

		setup_update_latest_extensions_button(frm);

		const response = await frappe.call({
      method: "service_warehouse.service_warehouse.doctype.tenant.tenant.get_session_tenant",
      args: {}
    });

    var tenant = response.message;
    if(tenant == null) {
      frappe.msgprint("You are not a tenant. Please contact your administrator.")
      return
    }
    // Return an object with the filters
    frm.set_query('service_packet', function() {
      return { 
          filters: {
              'docStatus': ['!=', '2'],
              'service_provider': ['=', tenant.service_provider]
          }
      };
    });
    frm.set_query('extensions', function() {
      return { 
          filters: {
              'service_provider': ['=', tenant.service_provider]
          }
      };
    });
	},
});

function setup_update_latest_extensions_button(frm) {
	frm.remove_custom_button(__("Update to Latest Extensions"));

	if (frm.doc.docstatus !== 0) {
		return;
	}

	const has_extensions = (frm.doc.extensions || []).some((row) => row.service_extension);
	if (!has_extensions) {
		return;
	}

	frm.add_custom_button(__("Update to Latest Extensions"), () => {
		update_extensions_to_latest(frm);
	});
}

function update_extensions_to_latest(frm) {
	const extensions = (frm.doc.extensions || [])
		.map((row) => row.service_extension)
		.filter(Boolean);

	if (!extensions.length) {
		frappe.msgprint(__("No extensions to update."));
		return;
	}

	frappe.call({
		method:
			"service_warehouse.service_marketplace.doctype.service_packet_version.service_packet_version.get_latest_extensions",
		args: { extensions },
		freeze: true,
		freeze_message: __("Finding latest extension versions..."),
		callback: (r) => {
			const latest = r.message || [];
			if (!latest.length) {
				frappe.msgprint(__("No latest extensions found."));
				return;
			}

			frm.clear_table("extensions");
			latest.forEach((name) => {
				frm.add_child("extensions", { service_extension: name });
			});
			frm.refresh_field("extensions");
			frm.dirty();

			frappe.show_alert({
				message: __("Extensions updated to latest versions ({0}).", [latest.length]),
				indicator: "green",
			});
		},
	});
}
