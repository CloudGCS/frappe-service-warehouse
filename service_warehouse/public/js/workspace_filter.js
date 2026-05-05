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
