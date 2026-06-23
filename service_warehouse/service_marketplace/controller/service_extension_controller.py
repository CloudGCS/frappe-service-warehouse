import re

import frappe
from frappe import _
from frappe.utils.file_manager import save_file

from service_warehouse.service_marketplace.doctype.service_extension.service_extension import (
	parse_manifest_version,
)
from service_warehouse.service_warehouse.doctype.tenant.tenant import get_session_tenant
from service_warehouse.utils.api_utils import APIResponse


REQUIRED_METADATA_FIELDS = (
	"extension_code",
	"title",
	"manifest_yaml",
	"sandbox_policy_json",
	"artifact_uri",
	"artifact_sha256",
)
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def _get_metadata():
	metadata = frappe.form_dict.get("metadata")
	if not metadata:
		return None, APIResponse.failed(message="metadata is required.", status_code=400)

	try:
		metadata = frappe.parse_json(metadata)
	except Exception:
		return None, APIResponse.failed(message="metadata must be valid JSON.", status_code=400)

	if not isinstance(metadata, dict):
		return None, APIResponse.failed(message="metadata must be a JSON object.", status_code=400)

	missing = [fieldname for fieldname in REQUIRED_METADATA_FIELDS if not str(metadata.get(fieldname) or "").strip()]
	if missing:
		return None, APIResponse.failed(
			message="Missing release fields: " + ", ".join(missing), status_code=400
		)

	return metadata, None


def _get_simulator_file():
	request = getattr(frappe, "request", None)
	files = getattr(request, "files", None)
	upload = files.get("simulator_file") if files else None
	if not upload:
		return None, APIResponse.failed(message="simulator_file upload is required.", status_code=400)
	return upload, None


def _validate_sandbox_policy(value):
	try:
		policy = frappe.parse_json(value)
	except Exception:
		return None, APIResponse.failed(message="Sandbox Policy must be valid JSON.", status_code=400)

	if not isinstance(policy, dict):
		return None, APIResponse.failed(message="Sandbox Policy must be a JSON object.", status_code=400)

	return value, None


def _get_boolean(value):
	if isinstance(value, bool):
		return value
	if value is None or value == "":
		return False
	if str(value).strip().lower() in {"1", "true", "yes"}:
		return True
	if str(value).strip().lower() in {"0", "false", "no"}:
		return False
	frappe.throw(_("is_background_plugin must be a boolean value."))


def _get_session_service_provider():
	tenant = get_session_tenant()
	if not tenant:
		return None, APIResponse.failed(message="You are not a tenant.", status_code=403)
	if not tenant.service_provider or not frappe.db.exists("Service Provider", tenant.service_provider):
		return None, APIResponse.failed(
			message="You are not a valid tenant with a defined service provider.", status_code=403
		)
	return tenant.service_provider, None


@frappe.whitelist()
def create_service_extension_release():
	metadata, error = _get_metadata()
	if error:
		return error

	upload, error = _get_simulator_file()
	if error:
		return error

	sandbox_policy_json, error = _validate_sandbox_policy(metadata["sandbox_policy_json"])
	if error:
		return error

	artifact_sha256 = str(metadata["artifact_sha256"]).strip().lower()
	if not SHA256_PATTERN.fullmatch(artifact_sha256):
		return APIResponse.failed(message="artifact_sha256 must be a SHA-256 digest.", status_code=400)

	try:
		major, minor = parse_manifest_version(metadata["manifest_yaml"])
		is_background_plugin = _get_boolean(metadata.get("is_background_plugin"))
	except frappe.ValidationError as error:
		return APIResponse.failed(message=str(error), status_code=400)

	service_provider, error = _get_session_service_provider()
	if error:
		return error

	extension_code = str(metadata["extension_code"]).strip()
	library_name = str(metadata.get("library_name") or extension_code).strip()
	extension_type = str(metadata.get("extension_type") or "MC Plugin").strip()

	if frappe.db.exists(
		"Service Extension",
		{
			"service_provider": service_provider,
			"library_name": library_name,
			"extension_type": extension_type,
			"major": major,
			"minor": minor,
		},
	):
		return APIResponse.failed(
			message="A Service Extension with the same library, extension type, and version already exists.",
			status_code=409,
		)

	doc = frappe.get_doc(
		{
			"doctype": "Service Extension",
			"extension_code": extension_code,
			"title": str(metadata["title"]).strip(),
			"service_provider": service_provider,
			"extension_type": extension_type,
			"library_name": library_name,
			"major": major,
			"minor": minor,
			"description": str(metadata.get("description") or ""),
			"is_background_plugin": is_background_plugin,
			"manifest_yaml": metadata["manifest_yaml"],
			"sandbox_policy_json": sandbox_policy_json,
			"artifact_uri": str(metadata["artifact_uri"]).strip(),
			"artifact_sha256": artifact_sha256,
		}
	)

	try:
		doc.insert(ignore_permissions=True)
	except frappe.ValidationError as error:
		return APIResponse.failed(message=str(error), status_code=400)

	file_doc = save_file(
		getattr(upload, "filename", None) or "simulator-plugin.zip",
		upload.read(),
		doc.doctype,
		doc.name,
		is_private=1,
		df="simulator_file",
	)
	doc.simulator_file = file_doc.file_url
	doc.save(ignore_permissions=True)

	return APIResponse.success(
		data={
			"name": doc.name,
			"service_provider": doc.service_provider,
			"extension_code": doc.extension_code,
			"library_name": doc.library_name,
			"major": doc.major,
			"minor": doc.minor,
			"simulator_file": doc.simulator_file,
		},
		message="Service Extension release created successfully.",
	)
