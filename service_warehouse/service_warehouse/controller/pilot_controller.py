import frappe
import uuid
from service_warehouse.utils.api_utils import APIResponse

PILOT_ROLE = "Pilot Role"


def get_pilot_profile_permission_query(user=None):
    """
    - System Manager / Host: all profiles
    - Tenant: all active profiles (Available Pilots)
    - Pilot Role: only own profile
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    if "System Manager" in roles or "Host" in roles:
        return ""

    if "Tenant" in roles:
        return "`tabPilot Profile`.`status` = 'Active'"

    if PILOT_ROLE in roles:
        return f"`tabPilot Profile`.`user` = {frappe.db.escape(user)}"

    return "1=0"


def sync_pilot_profile_phone_from_user(doc, method=None):
    """Sync User.mobile_no to Pilot Profile.phone when User is updated."""
    profile_name = frappe.db.get_value("Pilot Profile", {"user": doc.name}, "name")
    if not profile_name:
        return
    current_phone = frappe.db.get_value("Pilot Profile", profile_name, "phone")
    if current_phone != (doc.mobile_no or ""):
        frappe.db.set_value("Pilot Profile", profile_name, "phone", doc.mobile_no or "")


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
    profile.phone = doc.mobile_no or ""
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


def get_pilot_flight_log_permission_query(user=None):
    """
    - System Manager / Host: all logs
    - Pilot Role: only logs belonging to their own Pilot Profile
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
        return f"`tabPilot Flight Log`.`pilot` = {frappe.db.escape(profile_name)}"

    return "1=0"


@frappe.whitelist(allow_guest=True)
def register_pilot(full_name: str, email: str, password: str, phone: str = None):
    """Self-registration endpoint for pilots. Creates a User with Pilot Role."""
    if not full_name or not email or not password:
        return APIResponse.failed(message="All fields are required", status_code=400)

    if frappe.db.exists("User", email):
        return APIResponse.failed(message="A user with this email already exists", status_code=409)

    if len(password) < 8:
        return APIResponse.failed(message="Password must be at least 8 characters", status_code=400)

    try:
        user = frappe.new_doc("User")
        user.email = email
        user.first_name = full_name
        user.mobile_no = phone or ""
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
