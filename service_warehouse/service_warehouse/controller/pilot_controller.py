import frappe
import uuid
from frappe.utils import get_system_timezone
from service_warehouse.utils.api_utils import APIResponse

PILOT_ROLE = "Pilot Role"


def _normalize_phone(value):
    if not isinstance(value, str):
        return value

    value = value.strip()
    return value or None


def _normalize_time_zone(value):
    if not isinstance(value, str):
        return value

    value = value.strip()
    return value or None


def get_pilot_profile_permission_query(user=None):
    """
    - System Manager / Host: all profiles
    - Tenant: all active profiles (Available Pilots)
    - Pilot Role: all profiles, but edit is still restricted by has_permission
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    if "System Manager" in roles or "Host" in roles:
        return ""

    if "Tenant" in roles:
        return "`tabPilot Profile`.`status` = 'Active'"

    if PILOT_ROLE in roles:
        return ""

    return "1=0"


def sync_pilot_profile_from_user(doc, method=None):
    """Sync User fields to Pilot Profile when User is updated."""
    profile_name = frappe.db.get_value("Pilot Profile", {"user": doc.name}, "name")
    if not profile_name:
        return

    normalized_phone = _normalize_phone(doc.phone)
    normalized_time_zone = _normalize_time_zone(doc.time_zone)
    current_values = frappe.db.get_value(
        "Pilot Profile", profile_name, ["phone", "time_zone"], as_dict=True
    )

    updates = {}
    if current_values.phone != normalized_phone:
        updates["phone"] = normalized_phone
    if current_values.time_zone != normalized_time_zone:
        updates["time_zone"] = normalized_time_zone

    if updates:
        frappe.db.set_value("Pilot Profile", profile_name, updates, update_modified=False)


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
    profile.phone = _normalize_phone(doc.phone)
    profile.time_zone = _normalize_time_zone(doc.time_zone)
    profile.owner = doc.name
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
        fields=["pilot_id", "full_name", "email", "phone", "time_zone", "user", "name"],
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
def get_pilot_by_pilot_id(pilot_id: str = None, pilot_email: str = None):
    """Returns pilot information by PilotID or email. Called from Tenant/Service Boxes."""
    if not pilot_id and not pilot_email:
        return APIResponse.failed(message="pilot_id or pilot_email is required", status_code=400)

    if pilot_id:
        filters = {"pilot_id": pilot_id}
    else:
        # Lookup by the User linked to this Pilot Profile
        user_name = frappe.db.get_value("User", {"email": pilot_email}, "name")
        if not user_name:
            return APIResponse.failed(message="Pilot not found", status_code=404)
        filters = {"user": user_name}

    profile = frappe.db.get_value(
        "Pilot Profile",
        filters,
        ["pilot_id", "full_name", "email", "phone", "time_zone", "name", "status"],
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
def upsert_pilot_flight(**kwargs):
    """Writes flight data received from a Tenant Box into Pilot Flight."""
    pilot_id = kwargs.get("pilot_id")
    source_flight_id = kwargs.get("source_flight_id")
    tenant_code = kwargs.get("tenant_code")

    if not pilot_id or not source_flight_id or not tenant_code:
        return APIResponse.failed(message="pilot_id, source_flight_id and tenant_code are required", status_code=400)

    profile_name = frappe.db.get_value("Pilot Profile", {"pilot_id": pilot_id}, "name")
    if not profile_name:
        return APIResponse.failed(message="Pilot not found", status_code=404)

    existing = frappe.db.get_value(
        "Pilot Flight",
        {"pilot": profile_name, "source_flight_id": source_flight_id},
        "name",
    )

    if existing:
        log = frappe.get_doc("Pilot Flight", existing)
    else:
        log = frappe.new_doc("Pilot Flight")
        log.pilot = profile_name
        log.source_flight_id = source_flight_id

    log.tenant = tenant_code
    log.aircraft_name = kwargs.get("aircraft_name")
    log.flight_hours = float(kwargs.get("flight_hours") or 0)
    flight_date = kwargs.get("flight_date", "")
    log.flight_date = flight_date[:10] if flight_date else None
    log.location = kwargs.get("location")
    log.save(ignore_permissions=True)
    frappe.db.commit()
    return APIResponse.success()


def get_pilot_flight_permission_query(user=None):
    """
    - System Manager / Host: all flights
    - Pilot Role: only flights belonging to their own Pilot Profile
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    if "System Manager" in roles or "Host" in roles:
        return ""

    if PILOT_ROLE in roles:
        profile_name = frappe.db.get_value("Pilot Profile", {"user": user}, "name")
        if not profile_name:
            return "1=0"
        return f"`tabPilot Flight`.`pilot` = {frappe.db.escape(profile_name)}"

    return "1=0"


def get_pilot_flight_log_permission_query(user=None):
    return get_pilot_flight_permission_query(user=user)


@frappe.whitelist(allow_guest=True)
def register_pilot(
    full_name: str, email: str, password: str, phone: str = None, time_zone: str = None
):
    """Self-registration endpoint for pilots. Creates a User with Pilot Role."""
    if not full_name or not email or not password:
        return APIResponse.failed(message="All fields are required", status_code=400)

    if frappe.db.exists("User", email):
        return APIResponse.failed(message="A user with this email already exists", status_code=409)

    if len(password) < 8:
        return APIResponse.failed(message="Password must be at least 8 characters", status_code=400)

    normalized_phone = _normalize_phone(phone)
    normalized_time_zone = _normalize_time_zone(time_zone) or get_system_timezone()

    try:
        user = frappe.new_doc("User")
        user.email = email
        user.first_name = full_name
        user.phone = normalized_phone
        user.time_zone = normalized_time_zone
        user.send_welcome_email = 0
        user.role_profile_name = "Pilot"
        user.module_profile = "Pilot"
        user.insert(ignore_permissions=True)

        from frappe.utils.password import update_password
        update_password(user.email, password)

        frappe.db.commit()
        return APIResponse.success(message="Registration successful. You can now log in.")
    except Exception as e:
        frappe.log_error(str(e), "Pilot Registration")
        return APIResponse.failed(message="Registration failed. Please try again.", status_code=500)
