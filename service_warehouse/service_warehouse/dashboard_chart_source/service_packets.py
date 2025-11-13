import frappe
from frappe.utils.dashboard import cache_source
from service_warehouse.service_warehouse.dashboard_chart_source.utils import handle_chart_parameters, fetch_chart_series_data, format_chart_data_with_periods
from frappe.model.docstatus import DocStatus

@frappe.whitelist()
def get_tenant_published_packets():
    return get_tenant_packages(False)

@frappe.whitelist()
def get_tenant_not_published_packets():
    return get_tenant_packages(True)

@frappe.whitelist()
def get_tenant_total_packets():
    return get_tenant_packages(None)

@frappe.whitelist()
def get_tenant_total_service_packet_version_count():
    tenant_doc = get_tenant_doc()
    if tenant_doc is None:
        return 0

    provider = frappe.get_doc("Service Provider", tenant_doc.provider_code)
    filters={"service_provider": provider.name}
    service_packet_list = frappe.get_all("Service Packet", filters=filters, fields=["name"])

    total_count = 0
    for service_packet in service_packet_list:
        count = frappe.db.count("Service Packet Version", {"service_packet": service_packet["name"]})
        total_count += count

    response = {
        "value": total_count or 0,
        "route_options": filters,
        "route": ["list", "Service Packet Version"]
    }
    return response

@frappe.whitelist()
@cache_source # Decorator to cache the chart data
def get_tenant_service_packet_version_chart(chart_name=None, chart=None, no_cache=None, filters=None, from_date=None, to_date=None, timespan=None, time_interval=None, heatmap_year=None):
    tenant_doc = get_tenant_doc()
    if tenant_doc is None:
        return None
    provider = frappe.get_doc("Service Provider", tenant_doc.provider_code)
    service_packet_list = frappe.get_all("Service Packet", filters={"service_provider": provider.name}, fields=["name"])

    labels = [service_packet["name"] for service_packet in service_packet_list]
    data_values = []

    for service_packet in service_packet_list:
        # Count packets matching this version
        count = frappe.db.count("Service Packet Version", {"service_packet": service_packet["name"]})
        data_values.append(count)

    return {
        "labels": labels,
        "datasets": [
            {
                "name": "Packets by Version",
                "values": data_values
            }
        ]
    }

def get_tenant_packages(isDraft: bool | None):
    tenant_doc = get_tenant_doc()
    if tenant_doc is None:
        return 0

    filters = {
        "service_provider": tenant_doc.name if tenant_doc else ""
    }

    if isDraft is True:
        filters["docstatus"] = ["!=", DocStatus.submitted()]
    elif isDraft is False:
        filters["docstatus"] = DocStatus.draft()
    else:
        pass

    packages = frappe.get_all(
        "Service Packet",
        filters=filters,
        order_by="creation desc",
    )

    response = {
        "value": len(packages) or 0,
        "route_options": filters,
        "route": ["list", "Service Packet"]
    }

    return response

def get_tenant_doc():
    user = frappe.session.user
    tenant = frappe.db.get_value("Tenant", filters={"user": user})
    if tenant is None:
        return None
    tenant_doc = frappe.get_doc("Tenant", tenant)
    return tenant_doc