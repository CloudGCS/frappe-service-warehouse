import frappe


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
     