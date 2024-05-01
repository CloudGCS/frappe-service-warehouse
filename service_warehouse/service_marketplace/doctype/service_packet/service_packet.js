// Copyright (c) 2024, a-techsyn and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Packet", {
	onload: async function(frm) {
    const response = await frappe.call({
      method: "service_warehouse.service_warehouse.doctype.tenant.tenant.check_tenant_subscription",
      args: {packet_name: frm.doc.name}
    });
    let isSubscriptionPossible = false;
    let tenant = null;
    if (response.message != null) {
      debugger;
      tenant = response.message.tenant  ;
      const isSubscribed = response.message.is_subscribed;
      isSubscriptionPossible = frm.doc.docStatus != 1 && frm.doc.service_provider != null && tenant != null && !isSubscribed;  
    }

    frm.set_df_property('subscribe', 'hidden', !isSubscriptionPossible);
    frm.set_df_property('is_system_packet', 'hidden', tenant == null || tenant.name == "HOST");
    frm.set_df_property('is_seed_data', 'hidden', tenant == null || tenant.name != "HOST");
},
  before_submit: function(frm) {
    if (frm.doc.latest_release == null) {
      frappe.throw("You have no version of this packet. Please add a version before submitting."  );
      return false;
    }
  },
  subscribe: function(frm){
    frappe.call({
      method: "service_warehouse.service_marketplace.doctype.service_packet.service_packet.subscribe",
      args: {
        doc: frm.doc,
      },
      freeze: true,
      callback: function (r) {
        frappe.msgprint("Subscription successful. You can now use this packet.");
        frm.reload_doc();
      },
      error: (r) => {
        frappe.msgprint("Something went wrong, please try again later\n" + r.message);
      }
    });
  }
});
