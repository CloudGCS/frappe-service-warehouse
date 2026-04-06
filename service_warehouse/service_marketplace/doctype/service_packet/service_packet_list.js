// Copyright (c) 2024, a-techsyn and contributors
// For license information, please see license.txt

frappe.listview_settings["Service Packet"] = {
	onload: function (listview) {
		frappe._sw_sp_subscriptions = null;

		const $checkbox = listview.page.add_check(__("Subscribed"));
		$checkbox.on("change", function () {
			if ($(this).is(":checked")) {
				const names = Array.from(frappe._sw_sp_subscriptions || []);
				if (!names.length) {
					frappe.msgprint(__("You have no subscriptions."));
					$(this).prop("checked", false);
					return;
				}
				listview.filter_area.add([["Service Packet", "name", "in", names.join(",")]]);
			} else {
				listview.filter_area.remove("name");
			}
		});

		frappe.call({
			method: "service_warehouse.service_marketplace.doctype.service_packet.service_packet.get_subscribed_packets",
			callback: function (r) {
				frappe._sw_sp_subscriptions = new Set(r.message || []);
				listview.refresh();
			},
		});
	},
	formatters: {
		is_subscribed: function (value, df, doc) {
			const subscribed =
				frappe._sw_sp_subscriptions && frappe._sw_sp_subscriptions.has(doc.name);
			return `<span class="indicator-pill ${subscribed ? "green" : "gray"}">${
				subscribed ? __("Yes") : __("No")
			}</span>`;
		},
	},
};
