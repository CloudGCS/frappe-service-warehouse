import json

import frappe
from frappe.utils.file_manager import save_file

from service_warehouse.service_warehouse.doctype.tenant.tenant import get_session_tenant
from service_warehouse.utils.api_utils import APIResponse


PS_PLUGIN_EXTENSION_TYPE = "PS Plugin"
REQUIRED_METADATA_FIELDS = (
	"extension_code",
	"title",
	"library_name",
	"build_file",
	"major",
	"minor",
)


def _get_session_tenant():
	tenant = get_session_tenant()
	if not tenant:
		return None, APIResponse.failed(message="You are not a tenant.", status_code=403)
	if not tenant.service_provider or not frappe.db.exists("Service Provider", tenant.service_provider):
		return None, APIResponse.failed(
			message="You are not a valid tenant with a defined service provider.", status_code=403
		)
	return tenant, None


def _resolve_service_provider(metadata, tenant):
	requested = metadata.get("service_provider")
	if requested is None or requested == "":
		return tenant.service_provider, False, None
	if not isinstance(requested, str):
		return None, False, APIResponse.failed(message="service_provider must be a string.", status_code=400)

	requested = requested.strip()
	if not requested:
		return tenant.service_provider, False, None
	if requested == tenant.service_provider:
		return requested, False, None
	if tenant.tenant_code != "HOST":
		return None, False, APIResponse.failed(
			message="You are not allowed to publish for another service provider.",
			status_code=403,
		)
	if not frappe.db.exists("Service Provider", requested):
		return None, False, APIResponse.failed(
			message=f"Service Provider '{requested}' does not exist.",
			status_code=400,
		)
	return requested, True, None


def _get_metadata():
	raw = frappe.form_dict.get("metadata")
	if not raw:
		return None, APIResponse.failed(message="metadata is required.", status_code=400)

	try:
		metadata = frappe.parse_json(raw)
	except Exception:
		return None, APIResponse.failed(message="metadata must be valid JSON.", status_code=400)

	if not isinstance(metadata, dict):
		return None, APIResponse.failed(message="metadata must be a JSON object.", status_code=400)

	missing = [
		fieldname
		for fieldname in REQUIRED_METADATA_FIELDS
		if metadata.get(fieldname) is None or str(metadata.get(fieldname)).strip() == ""
	]
	if missing:
		return None, APIResponse.failed(
			message="Missing metadata fields: " + ", ".join(missing), status_code=400
		)

	return metadata, None


def _get_build_file_upload():
	request = getattr(frappe, "request", None)
	files = getattr(request, "files", None) if request else None
	upload = files.get("build_file") if files else None
	if not upload:
		return None, APIResponse.failed(message="build_file upload is required.", status_code=400)

	stream = getattr(upload, "stream", None)
	content = stream.read() if stream else upload.read()
	if not content:
		return None, APIResponse.failed(message="build_file upload is empty.", status_code=400)

	return content, None


def _get_boolean(value):
	if isinstance(value, bool):
		return value, None
	if value is None or value == "":
		return False, None
	if str(value).strip().lower() in {"1", "true", "yes"}:
		return True, None
	if str(value).strip().lower() in {"0", "false", "no"}:
		return False, None
	return None, APIResponse.failed(message="is_background_plugin must be a boolean value.", status_code=400)


def _parse_config(value):
	if value is None or value == "":
		return "{}", None
	if isinstance(value, dict):
		return json.dumps(value), None
	if isinstance(value, str):
		try:
			parsed = frappe.parse_json(value)
		except Exception:
			return None, APIResponse.failed(message="config must be valid JSON.", status_code=400)
		if not isinstance(parsed, dict):
			return None, APIResponse.failed(message="config must be a JSON object.", status_code=400)
		return json.dumps(parsed), None
	return None, APIResponse.failed(message="config must be a JSON object.", status_code=400)


def _parse_version_part(value, fieldname):
	try:
		parsed = int(value)
	except (TypeError, ValueError):
		return None, APIResponse.failed(message=f"{fieldname} must be an integer.", status_code=400)
	if parsed < 0:
		return None, APIResponse.failed(message=f"{fieldname} must be non-negative.", status_code=400)
	return parsed, None


@frappe.whitelist()
def create_ps_plugin():
	"""Create a PS Plugin Service Extension for the caller's tenant service provider.

	HOST tenants may set metadata.service_provider to publish for another existing provider.
	"""
	metadata, error = _get_metadata()
	if error:
		return error

	tenant, error = _get_session_tenant()
	if error:
		return error

	service_provider, explicit_provider, error = _resolve_service_provider(metadata, tenant)
	if error:
		return error

	extension_code = str(metadata["extension_code"]).strip()
	title = str(metadata["title"]).strip()
	library_name = str(metadata["library_name"]).strip()
	build_file_name = str(metadata["build_file"]).strip()
	description = str(metadata.get("description") or "")

	if "_" in extension_code:
		return APIResponse.failed(message="extension_code cannot contain underscore.", status_code=400)

	major, error = _parse_version_part(metadata["major"], "major")
	if error:
		return error
	minor, error = _parse_version_part(metadata["minor"], "minor")
	if error:
		return error

	is_background_plugin, error = _get_boolean(metadata.get("is_background_plugin"))
	if error:
		return error

	config, error = _parse_config(metadata.get("config"))
	if error:
		return error

	existing_name = frappe.db.exists(
		"Service Extension",
		{
			"service_provider": service_provider,
			"library_name": library_name,
			"extension_type": PS_PLUGIN_EXTENSION_TYPE,
			"major": major,
			"minor": minor,
		},
	)
	if existing_name:
		existing = frappe.get_doc("Service Extension", existing_name)
		return APIResponse.success(
			data=_plugin_response_data(existing, build_file_name, skipped=True),
			message="PS Plugin already exists; skipped without update.",
		)

	upload_bytes, error = _get_build_file_upload()
	if error:
		return error

	doc = frappe.get_doc(
		{
			"doctype": "Service Extension",
			"extension_code": extension_code,
			"title": title,
			"service_provider": service_provider,
			"extension_type": PS_PLUGIN_EXTENSION_TYPE,
			"library_name": library_name,
			"major": major,
			"minor": minor,
			"description": description,
			"is_background_plugin": 1 if is_background_plugin else 0,
			"config": config,
		}
	)
	if explicit_provider:
		doc.flags.explicit_service_provider = True

	try:
		doc.insert(ignore_permissions=True)
	except frappe.ValidationError as err:
		return APIResponse.failed(message=str(err), status_code=400)

	file_doc = save_file(
		build_file_name,
		upload_bytes,
		doc.doctype,
		doc.name,
		is_private=0,
		df="file",
	)
	doc.reload()
	doc.file = file_doc.file_url
	try:
		doc.save(ignore_permissions=True)
	except frappe.ValidationError as err:
		return APIResponse.failed(message=str(err), status_code=400)

	return APIResponse.success(
		data=_plugin_response_data(doc, build_file_name, skipped=False),
		message="PS Plugin created successfully.",
	)


def _plugin_response_data(doc, build_file_name, skipped=False):
	return {
		"name": doc.name,
		"service_provider": doc.service_provider,
		"extension_code": doc.extension_code,
		"title": doc.title,
		"library_name": doc.library_name,
		"build_file": build_file_name,
		"file": doc.file,
		"major": doc.major,
		"minor": doc.minor,
		"is_background_plugin": bool(doc.is_background_plugin),
		"config": frappe.parse_json(doc.config or "{}"),
		"description": doc.description or "",
		"skipped": skipped,
	}
