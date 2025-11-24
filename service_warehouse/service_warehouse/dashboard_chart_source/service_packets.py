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

@frappe.whitelist()
def get_subscribed_packets_for_host():
    return get_subscribed_packets()


@frappe.whitelist()
def get_subscribed_packets_for_tenant():
    tenant_doc = get_tenant_doc()
    if tenant_doc is None:
        return {}

    filters = {"tenant": tenant_doc.name}
    return get_subscribed_packets(filters)

def get_subscribed_packets(filter={}):
    service_subscription_list = frappe.get_all(
        "Service Subscription", filters=filter, fields=["name", "service_packet", "provider", "tenant"]
    )

    # Build a lookup of packet -> status/docstatus
    packet_names = list({d["service_packet"] for d in service_subscription_list})
    packet_rows = frappe.get_all(
        "Service Packet",
        filters={"name": ["in", packet_names]} if packet_names else {},
        fields=["name", "docstatus"]
    )
    packet_map = {r["name"]: r for r in packet_rows}
    docstatus_label = {0: "Draft", 1: "Submitted", 2: "Cancelled"}

    grouped = defaultdict(list)
    for d in service_subscription_list:
        pkt = packet_map.get(d["service_packet"], {})
        # Prefer explicit status field; fallback to docstatus label
        pkt_status = pkt.get("status")
        if not pkt_status and "docstatus" in pkt:
            pkt_status = docstatus_label.get(pkt["docstatus"], str(pkt["docstatus"]))

        processed_sb = {
            "name": d["name"],
            "service_packet": d["service_packet"],
            "provider": d["provider"],
            "tenant": d["tenant"],
            "status": pkt_status,
        }
        grouped[processed_sb["tenant"]].append(processed_sb)

    return dict(grouped)

@frappe.whitelist()
def get_host_server_boxes_info():
    return get_server_boxes_info({})


@frappe.whitelist()
def get_top_service_packets(limit=5):
    raw_results = frappe.db.get_all(
        "Service Subscription",
        fields=["service_packet", "count(name) as total"],
        group_by="service_packet",
        order_by="total desc"
    )

    final_results = []

    for row in raw_results:
        packet = frappe.db.get_value(
            "Service Packet",
            row.service_packet,
            ["title", "is_system_packet"],
            as_dict=True
        )

        if packet and not packet.is_system_packet:
            final_results.append({
                "service_packet": row.service_packet,
                "total": row.total,
                "title": packet.title
            })

        if len(final_results) >= limit:
            break

    return final_results



@frappe.whitelist()
def get_tenant_server_boxes_info():
    filter = {}
    tenant_doc = get_tenant_doc()
    if tenant_doc is not None:
        filter["tenant"] = tenant_doc.name
    return get_server_boxes_info(filter)

def get_server_boxes_info(filter):
    server_box_version_list = frappe.get_all(
        "Server Box Version",
        fields=["name", "version_name"],
        order_by="name desc",
    )

    if not server_box_version_list:
        return {}

    version_name_map = {
        v["name"]: v["version_name"]
        for v in server_box_version_list
    }

    latest_version = server_box_version_list[0]["name"]

    box_list = frappe.get_all("Server Box", fields=["name"], filters=filter)
    server_box_docs = [frappe.get_doc("Server Box", sb.name) for sb in box_list]

    service_packet_versions = frappe.get_all(
        "Service Packet",
        fields=["name", "latest_release"]
    )
    latest_by_packet = {sp["name"]: sp["latest_release"] for sp in service_packet_versions}

    processed_boxes = []

    for sb in server_box_docs:

        miss_update = False
        lack_update = False

        if sb.server_box_version != latest_version:
            lack_update = True

        if not sb.service_packet_versions:
            sb.miss_update = miss_update
            sb.lack_update = lack_update
        else:
            for spv in sb.service_packet_versions:
                packet_name = frappe.get_value(
                    "Service Packet Version",
                    spv.service_packet_version,
                    "service_packet"
                )

                latest_release = latest_by_packet.get(packet_name)

                if latest_release and latest_release != spv.service_packet_version:
                    if lack_update:
                        miss_update = True
                        lack_update = False
                    break

            sb.miss_update = miss_update
            sb.lack_update = lack_update

        sb.server_box_version = version_name_map.get(
            int(sb.server_box_version),
            sb.server_box_version
        )

        processed_boxes.append({
            "name": sb.name,
            "tenant": sb.tenant,
            "box_name": getattr(sb, "box_name", sb.name),
            "server_box_version": sb.server_box_version,
            "miss_update": miss_update,
            "lack_update": lack_update,
        })

    grouped = defaultdict(list)
    for sb in processed_boxes:
        grouped[sb["tenant"]].append(sb)

    return {
        "latest_version": version_name_map.get(
            latest_version,
            latest_version
        ),
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