import frappe
import uuid
from service_warehouse.utils.api_utils import APIResponse

PILOT_ROLE = "Pilot Role"


def create_pilot_profile_if_pilot(doc, method=None):
    """
    When a User is created, if they have the Pilot Role,
    automatically creates a Pilot Profile and assigns a PilotID.
    """
    has_pilot_role = any(r.role == PILOT_ROLE for r in doc.get("roles", []))
    if not has_pilot_role:
        return

    existing = frappe.db.exists("Pilot Profile", {"user": doc.name})
    if existing:
        return

    pilot_id = _generate_pilot_id()
    profile = frappe.new_doc("Pilot Profile")
    profile.pilot_id = pilot_id
    profile.user = doc.name
    profile.status = "Active"
    profile.insert(ignore_permissions=True)
    frappe.db.commit()


def _generate_pilot_id():
    """Generates a unique ID in PILOT-XXXXXX format."""
    while True:
        suffix = uuid.uuid4().hex[:6].upper()
        candidate = f"PILOT-{suffix}"
        if not frappe.db.exists("Pilot Profile", {"pilot_id": candidate}):
            return candidate


@frappe.whitelist()
def get_available_pilots():
    """Returns a list of all active pilots."""
    profiles = frappe.get_all(
        "Pilot Profile",
        filters={"status": "Active"},
        fields=["pilot_id", "full_name", "email", "phone", "user", "name"],
    )
    for profile in profiles:
        certs = frappe.get_all(
            "Pilot Certificate",
            filters={"parent": profile["name"]},
            fields=["certificate_name", "certificate_file", "expiry_date"],
        )
        profile["certificates"] = certs
    return APIResponse.success(data=profiles)


@frappe.whitelist()
def get_pilot_by_pilot_id(pilot_id: str):
    """Returns pilot information by PilotID. Called from the Tenant Box."""
    if not pilot_id:
        return APIResponse.failed(message="pilot_id is required", status_code=400)

    profile = frappe.db.get_value(
        "Pilot Profile",
        {"pilot_id": pilot_id},
        ["pilot_id", "full_name", "email", "phone", "name", "status"],
        as_dict=True,
    )
    if not profile:
        return APIResponse.failed(message="Pilot not found", status_code=404)

    certs = frappe.get_all(
        "Pilot Certificate",
        filters={"parent": profile["name"]},
        fields=["certificate_name", "certificate_file", "expiry_date"],
    )
    profile["certificates"] = certs
    return APIResponse.success(data=profile)


@frappe.whitelist(allow_guest=False)
def upsert_pilot_flight_log(**kwargs):
    """Writes flight data received from a Tenant Box into the Pilot Flight Log."""
    pilot_id = kwargs.get("pilot_id")
    source_flight_id = kwargs.get("source_flight_id")
    tenant_code = kwargs.get("tenant_code")

    if not pilot_id or not source_flight_id or not tenant_code:
        return APIResponse.failed(message="pilot_id, source_flight_id and tenant_code are required", status_code=400)

    profile_name = frappe.db.get_value("Pilot Profile", {"pilot_id": pilot_id}, "name")
    if not profile_name:
        return APIResponse.failed(message="Pilot not found", status_code=404)

    existing = frappe.db.get_value(
        "Pilot Flight Log",
        {"pilot": profile_name, "source_flight_id": source_flight_id},
        "name",
    )

    if existing:
        log = frappe.get_doc("Pilot Flight Log", existing)
    else:
        log = frappe.new_doc("Pilot Flight Log")
        log.pilot = profile_name
        log.source_flight_id = source_flight_id

    log.tenant = tenant_code
    log.aircraft_name = kwargs.get("aircraft_name")
    log.flight_hours = float(kwargs.get("flight_hours") or 0)
    flight_date = kwargs.get("flight_date", "")
    log.flight_date = flight_date[:10] if flight_date else None
    log.save(ignore_permissions=True)
    frappe.db.commit()
    return APIResponse.success()
