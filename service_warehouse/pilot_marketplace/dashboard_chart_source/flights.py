import frappe
from frappe import _
from frappe.utils.dashboard import cache_source


def _seconds_to_hours(value):
	try:
		return round(float(value or 0) / 3600, 1)
	except (TypeError, ValueError):
		return 0.0


@frappe.whitelist()
@cache_source
def get_my_flight_hours_by_tenant(
	chart_name=None,
	chart=None,
	no_cache=None,
	filters=None,
	from_date=None,
	to_date=None,
	timespan=None,
	time_interval=None,
	heatmap_year=None,
):
	profile_name = frappe.db.get_value("Pilot Profile", {"user": frappe.session.user}, "name")
	if not profile_name:
		return {"labels": [], "datasets": [{"name": _("Flight Hours"), "values": []}]}

	rows = frappe.db.sql(
		"""
		select
			coalesce(nullif(tenant_name, ''), tenant, 'Unknown Tenant') as tenant_label,
			sum(flight_hours) as total_seconds
		from `tabPilot Flight`
		where pilot = %s and docstatus < 2
		group by coalesce(nullif(tenant_name, ''), tenant, 'Unknown Tenant')
		order by total_seconds desc, tenant_label asc
		limit 8
		""",
		(profile_name,),
		as_dict=True,
	)

	return {
		"labels": [row.tenant_label for row in rows],
		"datasets": [
			{
				"name": _("Flight Hours"),
				"values": [_seconds_to_hours(row.total_seconds) for row in rows],
			}
		],
	}

