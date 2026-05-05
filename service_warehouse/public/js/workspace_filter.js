// Pilot Role workspace customizations
(function () {
	function isRealPilot() {
		if (!frappe || !frappe.user_roles) return false;
		var roles = frappe.user_roles;
		return roles.indexOf("Pilot Role") !== -1 && roles.indexOf("System Manager") === -1;
	}

	function hidePilotWorkspaceIfNotPilot() {
		if (isRealPilot()) return;

		document.querySelectorAll('a.item-anchor[href="/app/my-pilot-profile"]').forEach(function (el) {
			var container = el.closest(".sidebar-item-container");
			if (container) container.style.display = "none";
		});
	}

	// Redirect logo click to My Pilot Profile for real pilots
	function setupLogoRedirectForPilot() {
		if (!isRealPilot()) return;

		var logo = document.querySelector("a.navbar-brand.navbar-home");
		if (logo && !logo.dataset.pilotPatched) {
			logo.dataset.pilotPatched = "1";
			logo.addEventListener("click", function (e) {
				e.preventDefault();
				frappe.set_route("my-pilot-profile");
			});
		}
	}

	var observer = new MutationObserver(function () {
		hidePilotWorkspaceIfNotPilot();
		setupLogoRedirectForPilot();
	});

	$(document).ready(function () {
		var sidebar = document.querySelector(".desk-sidebar");
		if (sidebar) {
			observer.observe(sidebar, { childList: true, subtree: true });
		}
		hidePilotWorkspaceIfNotPilot();
		setupLogoRedirectForPilot();
	});

	$(document).on("page-change", function () {
		hidePilotWorkspaceIfNotPilot();
		setupLogoRedirectForPilot();
	});
})();

// Hide "Pilot" Role Profile from User form to prevent incorrect user creation

// Server-side filter via set_query (backup)
function _setPilotRoleProfileQuery(frm) {
	frm.set_query("role_profile_name", function () {
		return {
			filters: [["Role Profile", "name", "!=", "Pilot"]],
		};
	});
}

frappe.ui.form.on("User", {
	onload: function (frm) {
		_setPilotRoleProfileQuery(frm);
	},
	refresh: function (frm) {
		_setPilotRoleProfileQuery(frm);
	},
});

// DOM-level removal via MutationObserver
// Catches both dynamic option injection and hidden→visible transitions
(function () {
	function removePilotFromListbox(listbox) {
		var wrapper = listbox.closest(".awesomplete");
		if (!wrapper) return;
		var input = wrapper.querySelector('input[data-target="Role Profile"]');
		if (!input) return;
		listbox.querySelectorAll('[role="option"]').forEach(function (opt) {
			if (opt.querySelector('p[title="Pilot"]')) opt.remove();
		});
	}

	var observer = new MutationObserver(function (mutations) {
		mutations.forEach(function (mutation) {
			// Case 1: new option nodes added to a listbox
			mutation.addedNodes.forEach(function (node) {
				if (node.nodeType !== 1) return;
				if (node.getAttribute("role") === "option") {
					var listbox = node.parentElement;
					if (listbox && listbox.getAttribute("role") === "listbox") {
						removePilotFromListbox(listbox);
					}
				} else if (node.getAttribute("role") === "listbox") {
					removePilotFromListbox(node);
				}
			});
			// Case 2: hidden attribute removed = dropdown became visible
			if (
				mutation.type === "attributes" &&
				mutation.attributeName === "hidden" &&
				mutation.target.getAttribute("role") === "listbox" &&
				!mutation.target.hasAttribute("hidden")
			) {
				removePilotFromListbox(mutation.target);
			}
		});
	});

	$(document).ready(function () {
		observer.observe(document.body, {
			childList: true,
			subtree: true,
			attributes: true,
			attributeFilter: ["hidden"],
		});
	});
})();
