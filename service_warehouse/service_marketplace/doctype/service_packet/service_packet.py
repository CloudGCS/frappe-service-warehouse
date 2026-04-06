# Copyright (c) 2024, a-techsyn and contributors
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document
from frappe import _

from service_warehouse.service_warehouse.doctype.tenant.tenant import get_host_user, get_session_tenant

class ServicePacket(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		code_name: DF.Data
		description: DF.Text | None
		is_system_packet: DF.Check
		latest_release: DF.Link | None
		service_provider: DF.Link | None
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		self.check_for_underscore("Packet Code", self.code_name)

	def check_for_underscore(self, field_name, value):
		if "_" in value:
			frappe.throw(_(f"{field_name} cannot contain underscore for doc: {self.name}"))

	def before_insert(self):
		tenant = get_session_tenant()
		if not tenant:
			frappe.throw("You are not a tenant")

		if not frappe.db.exists("Service Provider", tenant.service_provider):
			frappe.throw("You are not a valid tenant with well defined service provider.")
		self.service_provider = tenant.service_provider

		if tenant.tenant_code == "HOST":
			self.is_system_packet = 1

		self._check_duplicate_from_other_owner()

	def _check_duplicate_from_other_owner(self):
		"""Prevent inserting a packet whose code_name already exists under a different owner."""
		existing_owner = frappe.db.get_value(
			"Service Packet",
			{"code_name": self.code_name},
			"owner",
		)
		if existing_owner and existing_owner != frappe.session.user:
			frappe.throw(_("You cannot duplicate a service packet that belongs to another user."))

	def on_submit(self):
		if not self.latest_release:
				frappe.throw("Please set the latest release before submitting.")

	def subscribe(self, tenant):

		if not tenant:
			frappe.throw("tenant is required to subscribe to a service packet.")

		# check for existing subscription with tenant and packet
		tenants_subscriptions = frappe.db.exists("Service Subscription", {"tenant": tenant.name, "service_packet": self.name})
		if tenants_subscriptions:
			frappe.throw("You are already subscribed to this service packet.")

		service_subscription = frappe.new_doc("Service Subscription")
		service_subscription.service_packet = self.name
		service_subscription.tenant = tenant.name
		service_subscription.insert(ignore_permissions=True)


@frappe.whitelist()
def get_subscribed_packets():
	from service_warehouse.service_warehouse.doctype.tenant.tenant import get_session_tenant
	tenant = get_session_tenant()
	if not tenant:
		return []
	return frappe.get_all(
		"Service Subscription",
		filters={"tenant": tenant.name},
		pluck="service_packet"
	)


# this method should be called on DocType Service Packet only.
@frappe.whitelist()
def subscribe(*args, **kwargs):
	service_packet = json.loads(kwargs.get('doc'))
	packet = frappe.get_doc("Service Packet", service_packet['name'])
	tenant = get_session_tenant()
	if not tenant:
		frappe.throw("You are not a tenant - you are not allowed to subscribe to this service packet.")
	packet.subscribe(tenant)
