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
