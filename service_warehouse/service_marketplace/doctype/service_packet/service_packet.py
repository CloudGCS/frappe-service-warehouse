# Copyright (c) 2024, a-techsyn and contributors
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document
from frappe import _

from service_warehouse.service_warehouse.doctype.tenant.tenant import get_host_user, get_session_tenant
from frappe.desk.reportview import compress, execute, get_form_params


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

		self._check_duplicate_from_other_owner()

		self.service_provider = tenant.service_provider

		if tenant.tenant_code == "HOST":
			self.is_system_packet = 1

	def _check_duplicate_from_other_owner(self):
		"""Prevent inserting a packet that belongs to another user.
		Must be called BEFORE self.service_provider is overwritten.
		"""
		# Check 1: code_name is globally unique – if it exists under any owner, block it.
		existing_owner = frappe.db.get_value(
			"Service Packet",
			{"code_name": self.code_name},
			"owner",
		)
		if existing_owner and existing_owner != frappe.session.user:
			frappe.throw(_("You cannot duplicate a service packet that belongs to another user."))

		# Check 2: exact match on the original service_provider (exact source record lookup).
		if self.service_provider:
			existing_owner = frappe.db.get_value(
				"Service Packet",
				{"service_provider": self.service_provider, "code_name": self.code_name},
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
	tenant = get_session_tenant()
	if not tenant:
		return []
	return frappe.get_all(
		"Service Subscription",
		filters={"tenant": tenant.name},
		pluck="service_packet"
	)


@frappe.whitelist()
@frappe.read_only()
def get_service_packet_list():
	"""Custom list endpoint that injects per-tenant subscription status and
	supports sorting by the virtual `is_subscribed` column."""

	args = get_form_params()

	# Detect whether the caller wants to sort by is_subscribed
	order_by = args.get("order_by") or ""
	sort_by_subscribed = "is_subscribed" in order_by
	sort_asc = order_by.lower().rstrip().endswith(" asc")

	# Replace the virtual sort column with a stable default so the DB query succeeds
	if sort_by_subscribed:
		args.order_by = "`tabService Packet`.`modified` desc"

	result = execute(**args)

	# Annotate every row with the current tenant's subscription status
	tenant = get_session_tenant()
	subscribed: set = set()
	if tenant:
		subscribed = set(
			frappe.get_all(
				"Service Subscription",
				filters={"tenant": tenant.name},
				pluck="service_packet",
			)
		)

	for row in result:
		row["is_subscribed"] = "Yes" if row.get("name") in subscribed else "No"

	# Sort in Python when the caller asked for is_subscribed ordering
	if sort_by_subscribed:
		# asc  → No first (N < Y); desc → Yes first (reverse alphabetical)
		result.sort(key=lambda x: x.get("is_subscribed", "No"), reverse=not sort_asc)

	return compress(result, args)


# this method should be called on DocType Service Packet only.
@frappe.whitelist()
def subscribe(*args, **kwargs):
	service_packet = json.loads(kwargs.get('doc'))
	packet = frappe.get_doc("Service Packet", service_packet['name'])
	tenant = get_session_tenant()
	if not tenant:
		frappe.throw("You are not a tenant - you are not allowed to subscribe to this service packet.")
	packet.subscribe(tenant)
