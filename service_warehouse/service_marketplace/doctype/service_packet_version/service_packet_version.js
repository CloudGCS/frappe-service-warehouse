// Copyright (c) 2024, a-techsyn and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Packet Version", {
  refresh: async function(frm) {
		if (!frm.is_new() && frm.doc.owner && frm.doc.owner !== frappe.session.user) {
			frm.page.remove_menu_item(__("Duplicate"));
		}
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
