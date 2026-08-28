# Copyright (c) 2024, a-techsyn and contributors
# For license information, please see license.txt


import os
import re

import frappe
import yaml
from frappe.model.document import Document
from frappe import _
from service_warehouse.service_warehouse.doctype.tenant.tenant import get_host_user, get_session_tenant


MANIFEST_VERSION_PATTERN = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?(?:[-+].*)?$")
MANIFEST_VERSION_LINE_PATTERN = re.compile(r"^(version\s*:\s*)[^#\r\n]*?(\s*(?:#.*)?)$", re.MULTILINE)
IMMUTABLE_FIELDNAMES = (
	"extension_code",
	"title",
	"service_provider",
	"extension_type",
	"library_name",
	"major",
	"minor",
	"description",
	"is_background_plugin",
	"is_build_in",
	"config",
)


def parse_manifest_version(manifest_yaml):
	"""Return the packed warehouse major/minor values from a manifest version."""
	if not manifest_yaml:
		frappe.throw(_("Manifest YAML is required."))

	try:
		manifest = yaml.safe_load(manifest_yaml) or {}
	except yaml.YAMLError:
		frappe.throw(_("Manifest YAML must be valid YAML."))

	if not isinstance(manifest, dict):
		frappe.throw(_("Manifest YAML must be a YAML object."))

	version = str(manifest.get("version") or "").strip()
	match = MANIFEST_VERSION_PATTERN.fullmatch(version)
	if not match:
		frappe.throw(_("Manifest YAML version must look like x.y or x.y.z."))

	major_part, minor_part, patch_part = match.groups()
	return int(major_part), int(f"{minor_part}{patch_part or '0'}")


def set_manifest_version(manifest_yaml, version):
	"""Replace the top-level manifest version without reformatting the rest of the YAML."""
	updated_manifest, replacements = MANIFEST_VERSION_LINE_PATTERN.subn(
		lambda match: f"{match.group(1)}{version}{match.group(2)}", manifest_yaml, count=1
	)
	if not replacements:
		frappe.throw(_("Manifest YAML must include a top-level version field."))
	return updated_manifest

class ServiceExtension(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from service_warehouse.service_marketplace.doctype.service_extension_file.service_extension_file import ServiceExtensionFile

		artifact_sha256: DF.Data | None
		artifact_uri: DF.Data | None
		config: DF.JSON | None
		description: DF.Text | None
		extension_code: DF.Data
		extension_type: DF.Link
		file: DF.Attach | None
		files: DF.Table[ServiceExtensionFile]
		is_background_plugin: DF.Check
		is_build_in: DF.Check
		library_name: DF.Data
		major: DF.Int
		manifest_yaml: DF.Code | None
		minor: DF.Int
		sandbox_policy_json: DF.Code | None
		service_provider: DF.Link | None
		simulator_file: DF.Attach | None
		title: DF.Data
		version: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.check_for_underscore("Extension Code", self.extension_code)
		self.validate_manifest_version()
		self.validate_sandbox_policy()
		self.validate_artifact_sha256()
		self.validate_immutable_fields()
		self.rename_uploaded_file()

	def validate_manifest_version(self):
		if self.extension_type != "MC Plugin" or not self.manifest_yaml:
			return

		major, minor = parse_manifest_version(self.manifest_yaml)
		if self.is_new():
			has_major = self.major not in (None, "")
			has_minor = self.minor not in (None, "")
			if has_major or has_minor:
				if not has_major or not has_minor:
					frappe.throw(_("Both Major and Minor are required when setting a Service Extension version."))
				user_major = int(self.major)
				user_minor = int(self.minor)
				if (user_major, user_minor) != (major, minor):
					self.manifest_yaml = set_manifest_version(
						self.manifest_yaml, f"{user_major}.{user_minor}"
					)
				self.major = user_major
				self.minor = user_minor
				return

			self.major = major
			self.minor = minor
			return

		if not self.has_value_changed("manifest_yaml"):
			return

		old_doc = self.get_doc_before_save()
		if not old_doc or not old_doc.manifest_yaml:
			return

		try:
			old_major, old_minor = parse_manifest_version(old_doc.manifest_yaml)
		except frappe.ValidationError:
			return

		if (old_major, old_minor) == (self.major, self.minor) and (major, minor) != (
			self.major,
			self.minor,
		):
			frappe.throw(_("Manifest version cannot change an existing Service Extension release."))

	def validate_sandbox_policy(self):
		if not self.sandbox_policy_json:
			return

		try:
			policy = frappe.parse_json(self.sandbox_policy_json)
		except Exception:
			frappe.throw(_("Sandbox Policy must be valid JSON."))

		if not isinstance(policy, dict):
			frappe.throw(_("Sandbox Policy must be a JSON object."))

	def validate_artifact_sha256(self):
		if self.artifact_sha256 and not re.fullmatch(r"[0-9a-fA-F]{64}", self.artifact_sha256):
			frappe.throw(_("Artifact SHA256 must be a SHA-256 digest."))

	def validate_immutable_fields(self):
		if self.is_new():
			return

		old_doc = self.get_doc_before_save()
		if not old_doc:
			return

		for fieldname in IMMUTABLE_FIELDNAMES:
			if self.immutable_field_changed(fieldname, old_doc):
				frappe.throw(_("{0} cannot be changed after a Service Extension is created.").format(fieldname))

	def immutable_field_changed(self, fieldname, old_doc):
		return self.get(fieldname) != old_doc.get(fieldname)

	def check_for_underscore(self, field_name, value):
		if "_" in value:
			frappe.throw(_(f"{field_name} cannot contain underscore for doc: {self.name}"))

	def rename_uploaded_file(self):
		"""Rename uploaded file to libraryName@version.ext format"""
		if not self.file or not self.library_name:
			return

		# Check if file field changed
		if self.has_value_changed("file"):
			# Get the File document
			file_doc = frappe.get_doc("File", {"file_url": self.file})

			# Get file extension
			_, ext = os.path.splitext(self.file)

			# Create new filename: libraryName@version.ext
			new_filename = f"{self.library_name}@{self.major}.{self.minor}{ext}"

			# Get current file path
			old_path = frappe.get_site_path(file_doc.file_url.lstrip('/'))

			# Create new file path
			file_dir = os.path.dirname(old_path)
			new_path = os.path.join(file_dir, new_filename)

			# Rename physical file
			if os.path.exists(old_path) and old_path != new_path:
				os.rename(old_path, new_path)

				# Update File document with new filename and file_name
				file_doc.file_name = new_filename
				file_doc.file_url = os.path.join(os.path.dirname(file_doc.file_url), new_filename)
				file_doc.save(ignore_permissions=True)

				# Update self.file
				self.file = file_doc.file_url

				# Update self.file
				self.file = file_doc.file_url

	def before_insert(self):
		self.validate_manifest_version()
		user = frappe.session.user
		# todo: we need to make a better check for fixtures - this is a temporary fix
		if user == "Administrator" and self.service_provider == "SYSTEM":
			# todo: this will replace the file on every migrate operation - we need to make it better
			if self.file:
				file_name = self.file.split("/")[-1]
				current_dir = os.getcwd()
				file_path = f"{current_dir}/assets/service_warehouse/plugins/{file_name}"
				file_content = frappe.read_file(file_path)
				file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "attached_to_doctype": "Service Extension",
            "attached_to_name": self.name,
						"attached_to_field": "file",
						"is_private": 1,
            "content": file_content
        })
				# Insert the new File document
				file_doc.insert(ignore_links=True)
			return
		tenant = get_session_tenant()
		if not tenant:
			frappe.throw("You are not a tenant")
		if not frappe.db.exists("Service Provider", tenant.service_provider):
			frappe.throw("You are not a valid tenant with well defined service provider.")

		if self.flags.get("explicit_service_provider"):
			if not self.service_provider or not frappe.db.exists("Service Provider", self.service_provider):
				frappe.throw(_("Service Provider '{0}' does not exist.").format(self.service_provider))
			if tenant.tenant_code != "HOST" and self.service_provider != tenant.service_provider:
				frappe.throw(_("You are not allowed to publish for another service provider."))
		else:
			self.service_provider = tenant.service_provider

		if not self.is_version_valid():
			frappe.throw(_("A Service Extension with the same library, extension type, and version already exists."))

	def after_insert(self):
		if self.owner == "Administrator" and self.service_provider == "SYSTEM":
			self.owner = get_host_user()
			frappe.db.set_value("Service Extension", self.name, "owner", get_host_user())
		self.sync_attached_files()

	def on_update(self):
		self.sync_attached_files()

	def sync_attached_files(self):
		if not self.files:
			return
		for row in self.files:
			if not row.se_file:
				continue
			if frappe.db.exists("File", {"file_url": row.se_file, "attached_to_name": self.name}):
				continue
			file_doc = frappe.new_doc("File")
			file_doc.file_url = row.se_file
			file_doc.file_name = os.path.basename(row.se_file)
			file_doc.attached_to_doctype = self.doctype
			file_doc.attached_to_name = self.name
			file_doc.attached_to_field = "files"
			file_doc.insert(ignore_permissions=True)

	def is_version_valid(self):
		return not frappe.db.exists(
			"Service Extension",
			{
				"service_provider": self.service_provider,
				"library_name": self.library_name,
				"extension_type": self.extension_type,
				"major": self.major,
				"minor": self.minor,
			},
		)
