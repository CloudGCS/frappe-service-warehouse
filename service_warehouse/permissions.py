import frappe

PILOT_ROLE = "Pilot Role"


def filter_users(user):
    """
    Pilot rolündeki kullanıcılar yalnızca kendi User kaydını liste görünümünde görebilir.
    Diğer roller için kısıtlama uygulanmaz.
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    if PILOT_ROLE in roles and "System Manager" not in roles and "Host" not in roles:
        return "`tabUser`.`name` = {user}".format(user=frappe.db.escape(user))

    return ""


def user_has_permission(doc, user):
    """
    Pilot rolündeki kullanıcılar yalnızca kendi User dokümanını açabilir.
    Diğer roller için kısıtlama uygulanmaz.
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    if PILOT_ROLE in roles and "System Manager" not in roles and "Host" not in roles:
        return doc.name == user

    return True


def filter_server_boxes(user):
    """
    Tenant kullanıcılar yalnızca kendi Tenant'ına ait Server Box'ları görür.
    Host / System Manager tümünü görür.
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    if "System Manager" in roles or "Host" in roles:
        return ""

    tenant_name = frappe.db.get_value("Tenant", {"user": user}, "name")
    if tenant_name:
        return "`tabServer Box`.`tenant` = {tenant}".format(tenant=frappe.db.escape(tenant_name))

    return "1=0"


def filter_role_profiles(user):
    return "`tabRole Profile`.`name` != 'Pilot'"


def filter_service_packets(user):
  if not user:
    user = frappe.session.user

  # todo replace with some well-defined role check
  if user == "Administrator":
    return None

  tenant = frappe.get_doc("Tenant", {"user": user})  
  if tenant:
    # packets that belong to user or submitted by others
    return "(`tabService Packet`.owner = {user} or (`tabService Packet`.docstatus = 1 and `tabService Packet`.owner != {user}))".format(user=frappe.db.escape(user))
  else:
    return None
    
def filter_service_subscriptions(user):
  if not user:
    user = frappe.session.user

  # todo replace with some well-defined role check
  if user == "Administrator":
    return None

  tenant = frappe.get_doc("Tenant", {"user": user})  
  if tenant:
    name_of_tenant = tenant.name
    provider = tenant.service_provider
    # I should be able to see my subscriptions and those subsriptions to my packets
    return (
      "(`tabService Subscription`.tenant = {name_of_tenant}) or "
      "(`tabService Subscription`.provider = {provider})"
    ).format(
      name_of_tenant=frappe.db.escape(name_of_tenant), 
      provider=frappe.db.escape(provider)
    )
  else:
    return None 
     