import json
from io import BytesIO

import frappe
from frappe.tests.utils import FrappeTestCase
from werkzeug.datastructures import FileStorage

from service_warehouse.service_marketplace.controller.service_extension_controller import (
	create_ps_plugin,
)


class TestServiceExtensionController(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		suffix = frappe.generate_hash(length=8).upper()
		self.user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"ps-plugin-{suffix.lower()}@example.com",
				"first_name": "PS",
				"last_name": suffix,
			}
		).insert(ignore_permissions=True)
		self.tenant = frappe.get_doc(
			{
				"doctype": "Tenant",
				"tenant_code": f"TEN{suffix}",
				"tenant_name": f"PS Plugin Tenant {suffix}",
				"user": self.user.name,
				"provider_code": f"PRV{suffix}",
				"provider_title": f"PS Plugin Provider {suffix}",
			}
		).insert(ignore_permissions=True)
		frappe.set_user(self.user.name)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_create_ps_plugin_uses_session_provider_and_attaches_build_file(self):
		response = self._create_plugin()

		self.assertEqual(response["status"], "success")
		doc = frappe.get_doc("Service Extension", response["data"]["name"])
		self.assertEqual(doc.service_provider, self.tenant.service_provider)
		self.assertEqual(doc.extension_type, "PS Plugin")
		self.assertEqual((doc.major, doc.minor), (1, 0))
		self.assertEqual(doc.library_name, "map-plugin")
		self.assertTrue(doc.file)
		self.assertTrue(doc.is_background_plugin)

		file_doc = frappe.get_doc("File", {"file_url": doc.file})
		self.assertEqual(file_doc.attached_to_field, "file")

	def test_duplicate_library_version_is_skipped(self):
		first = self._create_plugin()
		self.assertEqual(first["status"], "success")
		self.assertFalse(first["data"]["skipped"])

		response = self._create_plugin()

		self.assertEqual(response["status"], "success")
		self.assertTrue(response["data"]["skipped"])
		self.assertEqual(response["data"]["name"], first["data"]["name"])
		self.assertIn("skipped without update", response["message"])

	def test_invalid_request_is_rejected(self):
		payload = self._payload()
		del payload["library_name"]
		response = self._call_controller(payload)
		self.assertEqual(response["status"], "failed")
		self.assertEqual(frappe.local.response["http_status_code"], 400)

		payload = self._payload()
		payload["config"] = "[]"
		response = self._call_controller(payload)
		self.assertEqual(response["status"], "failed")
		self.assertEqual(frappe.local.response["http_status_code"], 400)

		payload = self._payload()
		response = self._call_controller(payload, include_upload=False)
		self.assertEqual(response["status"], "failed")
		self.assertEqual(frappe.local.response["http_status_code"], 400)

		payload = self._payload()
		payload["extension_code"] = "bad_code"
		response = self._call_controller(payload)
		self.assertEqual(response["status"], "failed")
		self.assertEqual(frappe.local.response["http_status_code"], 400)

	def test_request_without_a_tenant_is_rejected(self):
		frappe.set_user("Administrator")

		response = self._call_controller(self._payload())

		self.assertEqual(response["status"], "failed")
		self.assertEqual(frappe.local.response["http_status_code"], 403)

	def test_host_can_publish_for_another_existing_provider(self):
		target_provider = self._create_service_provider()
		host = self._ensure_host_tenant()
		frappe.set_user(host.user)

		payload = self._payload()
		payload["extension_code"] = f"host{frappe.generate_hash(length=6).lower()}"
		payload["library_name"] = payload["extension_code"]
		payload["service_provider"] = target_provider
		response = self._call_controller(payload)

		self.assertEqual(response["status"], "success")
		self.assertFalse(response["data"]["skipped"])
		self.assertEqual(response["data"]["service_provider"], target_provider)
		doc = frappe.get_doc("Service Extension", response["data"]["name"])
		self.assertEqual(doc.service_provider, target_provider)
		self.assertTrue(doc.name.startswith(f"{target_provider}_"))

	def test_host_without_service_provider_uses_session_provider(self):
		host = self._ensure_host_tenant()
		frappe.set_user(host.user)

		payload = self._payload()
		payload["extension_code"] = f"host{frappe.generate_hash(length=6).lower()}"
		payload["library_name"] = payload["extension_code"]
		response = self._call_controller(payload)

		self.assertEqual(response["status"], "success")
		self.assertEqual(response["data"]["service_provider"], host.service_provider)
		doc = frappe.get_doc("Service Extension", response["data"]["name"])
		self.assertEqual(doc.service_provider, host.service_provider)

	def test_non_host_cannot_override_service_provider(self):
		payload = self._payload()
		payload["service_provider"] = "SYSTEM"
		response = self._call_controller(payload)

		self.assertEqual(response["status"], "failed")
		self.assertEqual(frappe.local.response["http_status_code"], 403)
		self.assertIn("another service provider", response["message"])

	def test_missing_service_provider_is_rejected(self):
		host = self._ensure_host_tenant()
		frappe.set_user(host.user)

		payload = self._payload()
		payload["extension_code"] = f"host{frappe.generate_hash(length=6).lower()}"
		payload["library_name"] = payload["extension_code"]
		payload["service_provider"] = "MISSINGPROVIDER"
		response = self._call_controller(payload)

		self.assertEqual(response["status"], "failed")
		self.assertEqual(frappe.local.response["http_status_code"], 400)
		self.assertIn("does not exist", response["message"])

	def _create_plugin(self):
		return self._call_controller(self._payload())

	def _ensure_host_tenant(self):
		frappe.set_user("Administrator")
		if frappe.db.exists("Tenant", "HOST"):
			host = frappe.get_doc("Tenant", "HOST")
			if not frappe.db.exists("User", host.user):
				frappe.get_doc(
					{
						"doctype": "User",
						"email": host.user,
						"first_name": "Host",
						"enabled": 1,
					}
				).insert(ignore_permissions=True)
			else:
				host_user = frappe.get_doc("User", host.user)
				if not host_user.enabled:
					host_user.enabled = 1
					host_user.save(ignore_permissions=True)
			return host

		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"host-{frappe.generate_hash(length=6).lower()}@example.com",
				"first_name": "Host",
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
		return frappe.get_doc(
			{
				"doctype": "Tenant",
				"tenant_code": "HOST",
				"tenant_name": "Host Tenant",
				"user": user.name,
				"provider_code": "SYSTEM",
				"provider_title": "System",
			}
		).insert(ignore_permissions=True)

	def _create_service_provider(self):
		frappe.set_user("Administrator")
		name = f"PRV{frappe.generate_hash(length=8).upper()}"
		doc = frappe.new_doc("Service Provider")
		doc.name = name
		doc.title = name
		doc.insert(ignore_permissions=True)
		return doc.name

	def _payload(self):
		return {
			"extension_code": f"ps{self.tenant.name[-8:].lower()}",
			"title": "Map Plugin",
			"library_name": "map-plugin",
			"build_file": "map-plugin.js",
			"is_background_plugin": True,
			"config": {"entry": "main"},
			"description": "Pilot Station map plugin",
			"major": 1,
			"minor": 0,
		}

	def _call_controller(self, payload, include_upload=True):
		frappe.local.form_dict = frappe._dict({"metadata": json.dumps(payload)})
		frappe.local.response = frappe._dict()
		frappe.local.request = frappe._dict()
		frappe.local.request.files = {}
		if include_upload:
			content = f"console.log({json.dumps(payload.get('extension_code') or 'map')});".encode()
			frappe.local.request.files["build_file"] = FileStorage(
				stream=BytesIO(content), filename="map-plugin.js"
			)
		return create_ps_plugin()
