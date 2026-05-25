// Pilot Role workspace customizations
(function () {
	function isRealPilot() {
		if (!frappe || !frappe.user_roles) return false;
		var roles = frappe.user_roles;
		return roles.indexOf("Pilot Role") !== -1 && roles.indexOf("System Manager") === -1;
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

	// Server Box ve Tenant list sayfalarında her kullanıcı için
	// breadcrumb workspace'ini "Dashboard-Tenant" olarak sabitle.
	var FORCE_TENANT_WORKSPACE = ["Server Box", "Tenant"];

	function patchBreadcrumbs() {
		if (!frappe || !frappe.breadcrumbs || frappe.breadcrumbs._swPatched) return;
		frappe.breadcrumbs._swPatched = true;

		var _origAdd = frappe.breadcrumbs.add.bind(frappe.breadcrumbs);
		frappe.breadcrumbs.add = function (module, doctype, type) {
			if (FORCE_TENANT_WORKSPACE.indexOf(doctype) !== -1) {
				var obj =
					typeof module === "object"
						? module
						: { module: module, doctype: doctype, type: type };
				obj.workspace = "Dashboard-Tenant";
				frappe.breadcrumbs.all[frappe.breadcrumbs.current_page()] = obj;
				frappe.breadcrumbs.update();
				return;
			}
			return _origAdd(module, doctype, type);
		};
	}

	var observer = new MutationObserver(function () {
		setupLogoRedirectForPilot();
	});

	$(document).ready(function () {
		var sidebar = document.querySelector(".desk-sidebar");
		if (sidebar) {
			observer.observe(sidebar, { childList: true, subtree: true });
		}
		setupLogoRedirectForPilot();
		patchBreadcrumbs();
	});

	$(document).on("page-change", function () {
		setupLogoRedirectForPilot();
	});
})();


