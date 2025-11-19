import frappe
from frappe.utils.dashboard import cache_source
from service_warehouse.service_warehouse.dashboard_chart_source.utils import handle_chart_parameters, fetch_chart_series_data, format_chart_data_with_periods
from frappe.model.docstatus import DocStatus
from collections import defaultdict

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
def get_tenant_total_subscribed_packeges_count():
    tenant_doc = get_tenant_doc()
    if tenant_doc is None:
        return 0

    filters={"tenant": tenant_doc.name}

    service_subscription_list = frappe.get_all(
        "Service Subscription", filters=filters, fields=["name"]
    )
    total_count = len(service_subscription_list) or 0,

    response = {
        "value": total_count,
        "route_options": filters,
        "route": ["list", "Service Subscription"]
    }
    return response

@frappe.whitelist()
def get_tenant_total_service_box_count():
    tenant_doc = get_tenant_doc()
    if tenant_doc is None:
        return 0

    filters={"tenant": tenant_doc.name}

    service_box_list = frappe.get_all(
        "Server Box", filters=filters, fields=["box_name"]
    )
    total_count = len(service_box_list) or 0,

    response = {
        "value": total_count,
        "route_options": filters,
        "route": ["list", "Server Box"]
    }
    return response

@frappe.whitelist(allow_guest=True)
def get_tenant_subscribed_packets():
    service_subscription_list = frappe.get_all(
        "Service Subscription", fields=["name", "service_packet", "provider", "tenant"]
    )
    grouped = defaultdict(list)
    for d in service_subscription_list:
        grouped[d["tenant"]].append(d)

    return dict(grouped)


@frappe.whitelist()
def get_outdated_server_boxes():
    # 1) En son sürümü bul
    latest_version_doc = frappe.get_all(
        "Server Box Version",
        order_by="name desc",
        limit_page_length=1
    )

    if not latest_version_doc:
        return {}

    latest_version = latest_version_doc[0]["name"]

    print("latest_version", latest_version)

    # 2) Tüm kutuları çek
    box_list = frappe.get_all(
        "Server Box",
        fields=["name", "box_name", "tenant", "server_box_version"]
    )

    print("box_list", box_list)

    # 3) Güncel olmayan kutuları filtrele
    outdated = [
        b for b in box_list
        if int(b["server_box_version"]) != latest_version
    ]

    grouped = defaultdict(list)

    for item in outdated:
        grouped[item["tenant"]].append(item)

    return {
        "latest_version": latest_version,
        "tenants": grouped,
    }


@frappe.whitelist()
@cache_source # Decorator to cache the chart data
def get_tenant_service_packet_version_chart(chart_name=None, chart=None, no_cache=None, filters=None, from_date=None, to_date=None, timespan=None, time_interval=None, heatmap_year=None):
    tenant_doc = get_tenant_doc()
    if not tenant_doc:
        return None

    provider = frappe.get_doc("Service Provider", tenant_doc.provider_code)
    packets = frappe.get_all(
        "Service Packet",
        filters={"service_provider": provider.name},
        pluck="name"
    )

    version_counts = [
        frappe.db.count("Service Packet Version", {"service_packet": name})
        for name in packets
    ]

    subs = frappe.get_all(
        "Service Subscription",
        filters={"service_packet": ["in", packets]},
        fields=["service_packet", "tenant"]
    )
    tenants_map = {}
    for row in subs:
        tenants_map.setdefault(row["service_packet"], set()).add(row["tenant"])

    tenant_counts = [len(tenants_map.get(name, [])) for name in packets]

    labels = packets

    return {
        "labels": labels,
        "datasets": [
            {"name": "Packet Versions", "values": version_counts},
            {"name": "Subscribed Tenants", "values": tenant_counts},
        ],
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