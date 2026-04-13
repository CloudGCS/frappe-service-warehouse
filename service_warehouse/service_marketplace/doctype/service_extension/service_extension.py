# Copyright (c) 2024, a-techsyn and contributors
# For license information, please see license.txt


import os
import frappe
from frappe.model.document import Document
from frappe import _
from service_warehouse.service_warehouse.doctype.tenant.tenant import get_host_user, get_session_tenant

class ServiceExtension(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from service_warehouse.service_marketplace.doctype.service_extension_file.service_extension_file import ServiceExtensionFile

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
		minor: DF.Int
		service_provider: DF.Link | None
		title: DF.Data
		version: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.check_for_underscore("Extension Code", self.extension_code)
		self.rename_uploaded_file()

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

		self._check_duplicate_from_other_owner()

		self.service_provider = tenant.service_provider

		if not self.is_version_valid():
			frappe.throw("Your version number should progress, can not be downgrading from the latest version created.")

	def _check_duplicate_from_other_owner(self):
		"""Prevent inserting an extension that is a copy of another user's extension.
		Must be called BEFORE self.service_provider is overwritten.
		"""
		if not self.service_provider:
			# New doc created from scratch – service_provider is empty, nothing to check.
			return
		existing_owner = frappe.db.get_value(
			"Service Extension",
			{
				"extension_code": self.extension_code,
				"extension_type": self.extension_type,
				"major": self.major,
				"minor": self.minor,
				"service_provider": self.service_provider,
			},
			"owner",
		)
		if existing_owner and existing_owner != frappe.session.user:
			frappe.throw(_("You cannot duplicate a service extension that belongs to another user."))

	def after_insert(self):
		if self.owner == "Administrator" and self.service_provider == "SYSTEM":
			self.owner = get_host_user()
			frappe.db.set_value("Service Extension", self.name, "owner", get_host_user())
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
		# self has major and minor version first retrive all the versions with same library name
		versions = frappe.get_all("Service Extension",
														filters={"service_provider": self.service_provider, "extension_code": self.extension_code, "extension_type": self.extension_type},
														fields=["major", "minor"])

		if not versions:
			return True
		# check if the version is greater
		for version in versions:
			if version.major > self.major:
				return False
			elif version.major == self.major and version.minor >= self.minor:
				return False
		return True