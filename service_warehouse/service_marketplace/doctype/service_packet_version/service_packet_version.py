# Copyright (c) 2024, a-techsyn and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from service_warehouse.service_warehouse.doctype.tenant.tenant import get_host_user, get_session_tenant


class ServicePacketVersion(Document):
  # begin: auto-generated types
  # This code is auto-generated. Do not modify anything in this block.

  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
    from frappe.types import DF
    from service_warehouse.service_marketplace.doctype.service_packet_extension.service_packet_extension import ServicePacketExtension

    amended_from: DF.Link | None
    extensions: DF.TableMultiSelect[ServicePacketExtension]
    major: DF.Int
    minor: DF.Int
    service_packet: DF.Link
    version: DF.Data | None
  # end: auto-generated types

  def validate(self):
    self._validate_unique_library_names()

  def before_insert(self):
    tenant = get_session_tenant()
    if tenant:
      self._check_duplicate_from_other_owner()
      is_valid_version = self.check_version()
      if not is_valid_version:
        frappe.throw("You are not allowed to add this version. Please check your major or minor values.")
    else:
      frappe.throw("You are not a tenant")

  def _check_duplicate_from_other_owner(self):
    """Prevent creating a version for a service packet owned by another user."""
    packet_owner = frappe.db.get_value("Service Packet", self.service_packet, "owner")
    if packet_owner and packet_owner != frappe.session.user:
      frappe.throw(_("You cannot duplicate a service packet version that belongs to another user."))

  def _validate_unique_library_names(self):
    """Ensure each library_name + extension_type appears at most once among selected extensions."""
    seen = {}
    for row in self.extensions or []:
      if not row.service_extension:
        continue
      library_name, extension_type = frappe.db.get_value(
        "Service Extension", row.service_extension, ["library_name", "extension_type"]
      ) or (None, None)
      if not library_name:
        continue
      key = (library_name, extension_type or "")
      if key in seen:
        frappe.throw(
          _("Service Extension with library name '{0}' and type '{1}' is selected more than once. Only one version per library and type is allowed.").format(
            library_name, extension_type or ""
          )
        )
      seen[key] = row.service_extension

  def on_submit(self):
    service_packet = frappe.get_doc("Service Packet", self.service_packet)
    service_packet.latest_release = self.name
    service_packet.save()

  def check_version(self):
    # self has major and minor version first retrive all the versions with same library name
    versions = frappe.get_all("Service Packet Version", filters={"service_packet": self.service_packet}, fields=["major", "minor"])
    if not versions:
      return True
    # check if the version is greater
    for version in versions:
      if version.major > self.major:
        return False
      elif version.major == self.major and version.minor >= self.minor:
        return False
    return True


@frappe.whitelist()
def get_latest_extensions(extensions):
  """Resolve attached Service Extensions to the latest version per library_name and type.

  Returns a list of Service Extension names (one per unique library_name + extension_type).
  """
  if isinstance(extensions, str):
    extensions = frappe.parse_json(extensions)

  if not extensions:
    return []

  extension_names = []
  for item in extensions:
    if isinstance(item, dict):
      name = item.get("service_extension") or item.get("name")
    else:
      name = item
    if name:
      extension_names.append(name)

  if not extension_names:
    return []

  current = frappe.get_all(
    "Service Extension",
    filters={"name": ["in", extension_names]},
    fields=["name", "library_name", "extension_type", "service_provider"],
  )

  # Keep first-seen service_provider per library_name + extension_type
  libraries = {}
  for ext in current:
    if not ext.library_name:
      continue
    key = (ext.library_name, ext.extension_type or "")
    if key not in libraries:
      libraries[key] = ext.service_provider

  latest_names = []
  for (library_name, extension_type), service_provider in libraries.items():
    filters = {"library_name": library_name}
    if extension_type:
      filters["extension_type"] = extension_type
    if service_provider:
      filters["service_provider"] = service_provider

    latest = frappe.get_all(
      "Service Extension",
      filters=filters,
      fields=["name"],
      order_by="major desc, minor desc",
      limit_page_length=1,
    )
    if latest:
      latest_names.append(latest[0].name)

  return latest_names
