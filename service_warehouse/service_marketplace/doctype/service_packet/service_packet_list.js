// Copyright (c) 2024, a-techsyn and contributors
// For license information, please see license.txt

frappe.listview_settings["Service Packet"] = {
	onload: function (listview) {
		// Route the list view through our custom endpoint so that each row
		// already carries the correct per-tenant `is_subscribed` value and
		// server-side sorting by that column works correctly.
		listview.method =
			"service_warehouse.service_marketplace.doctype.service_packet.service_packet.get_service_packet_list";

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

		// Fetch subscription names for the checkbox filter only
		// (display / sorting is now handled server-side)
		frappe.call({
			method: "service_warehouse.service_marketplace.doctype.service_packet.service_packet.get_subscribed_packets",
			callback: function (r) {
				frappe._sw_sp_subscriptions = new Set(r.message || []);
			},
		});
	},
	formatters: {
		is_subscribed: function (value) {
			// `value` is now populated by the server ("Yes" / "No")
			const subscribed = value === "Yes";
			return `<span class="indicator-pill ${subscribed ? "green" : "gray"}">${
				subscribed ? __("Yes") : __("No")
			}</span>`;
		},
	},
};
