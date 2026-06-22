import json
from io import BytesIO

import frappe
from frappe.tests.utils import FrappeTestCase
from werkzeug.datastructures import FileStorage

from service_warehouse.service_marketplace.controller.service_extension_controller import (
	create_service_extension_release,
)
from service_warehouse.service_marketplace.doctype.service_extension.service_extension import (
	parse_manifest_version,
)


class TestServiceExtensionController(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		suffix = frappe.generate_hash(length=8).upper()
		self.user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"release-{suffix.lower()}@example.com",
				"first_name": "Release",
				"last_name": suffix,
			}
		).insert(ignore_permissions=True)
		self.tenant = frappe.get_doc(
			{
				"doctype": "Tenant",
				"tenant_code": f"TEN{suffix}",
				"tenant_name": f"Release Tenant {suffix}",
				"user": self.user.name,
				"provider_code": f"PRV{suffix}",
				"provider_title": f"Release Provider {suffix}",
			}
		).insert(ignore_permissions=True)
		frappe.set_user(self.user.name)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_version_packing(self):
		self.assertEqual(parse_manifest_version("version: 1.2\n"), (1, 20))
		self.assertEqual(parse_manifest_version("version: 1.2.3\n"), (1, 23))

	def test_create_release_uses_session_provider_and_attaches_simulator_file(self):
		response = self._create_release(version="1.2.3")

		self.assertEqual(response["status"], "success")
		doc = frappe.get_doc("Service Extension", response["data"]["name"])
		self.assertEqual(doc.service_provider, self.tenant.service_provider)
		self.assertEqual((doc.major, doc.minor), (1, 23))
		self.assertEqual(doc.artifact_sha256, "a" * 64)
		self.assertTrue(doc.simulator_file.startswith("/private/files/"))

		file_doc = frappe.get_doc("File", {"file_url": doc.simulator_file})
		self.assertEqual(file_doc.attached_to_field, "simulator_file")
		self.assertTrue(file_doc.is_private)

	def test_duplicate_packed_library_version_is_rejected(self):
		self._create_release(version="1.2.30")

		response = self._create_release(version="1.23.0")

		self.assertEqual(response["status"], "failed")
		self.assertEqual(frappe.local.response["http_status_code"], 409)
		self.assertIn("same library version", response["message"])

	def test_only_release_artifact_fields_are_mutable(self):
		response = self._create_release(version="1.2")
		doc = frappe.get_doc("Service Extension", response["data"]["name"])

		doc.artifact_uri = "s3://bucket/updated-plugin.tar.gz"
		doc.save(ignore_permissions=True)
		doc.reload()
		self.assertEqual(doc.artifact_uri, "s3://bucket/updated-plugin.tar.gz")

		doc.title = "Changed title"
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)

		doc.reload()
		doc.manifest_yaml = "version: 1.3\n"
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)

	def test_invalid_request_is_rejected(self):
		payload = self._payload(version="1.2")
		payload["artifact_sha256"] = "not-a-checksum"
		response = self._call_controller(payload)
		self.assertEqual(response["status"], "failed")
		self.assertEqual(frappe.local.response["http_status_code"], 400)

		payload = self._payload(version="1.2")
		payload["sandbox_policy_json"] = "[]"
		response = self._call_controller(payload)
		self.assertEqual(response["status"], "failed")
		self.assertEqual(frappe.local.response["http_status_code"], 400)

		payload = self._payload(version="1.2")
		response = self._call_controller(payload, include_upload=False)
		self.assertEqual(response["status"], "failed")
		self.assertEqual(frappe.local.response["http_status_code"], 400)

		payload = self._payload(version="not-a-version")
		response = self._call_controller(payload)
		self.assertEqual(response["status"], "failed")
		self.assertEqual(frappe.local.response["http_status_code"], 400)

	def test_request_without_a_tenant_is_rejected(self):
		frappe.set_user("Administrator")

		response = self._call_controller(self._payload(version="1.2"))

		self.assertEqual(response["status"], "failed")
		self.assertEqual(frappe.local.response["http_status_code"], 403)

	def _create_release(self, version):
		return self._call_controller(self._payload(version=version))

	def _payload(self, version):
		return {
			"extension_code": f"release{self.tenant.name[-8:].lower()}",
			"title": "Release Plugin",
			"manifest_yaml": f"version: {version}\n",
			"sandbox_policy_json": '{"mode":"bubblewrap","profile":"default"}',
			"artifact_uri": "s3://bucket/plugin.tar.gz",
			"artifact_sha256": "A" * 64,
		}

	def _call_controller(self, payload, include_upload=True):
		frappe.local.form_dict = frappe._dict({"metadata": json.dumps(payload)})
		frappe.local.response = frappe._dict()
		frappe.local.request = frappe._dict()
		frappe.local.request.files = {}
		if include_upload:
			frappe.local.request.files["simulator_file"] = FileStorage(
				stream=BytesIO(b"simulator zip bytes"), filename="simulator-plugin.zip"
			)
		return create_service_extension_release()
