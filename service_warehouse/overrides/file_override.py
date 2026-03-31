# Copyright (c) 2024, CloudGCS and contributors
# For license information, please see license.txt

import frappe
import os
from frappe import _
import hashlib


def validate_file(doc, method):
	"""
	Prevent uploading a file with the same content hash as an existing file
	attached to the 'file' field of a Service Extension
	"""
	if doc.attached_to_doctype != "Service Extension" or not doc.attached_to_name:
		return

	if doc.attached_to_field != "file":
		return

	# Compute content_hash if Frappe hasn't set it yet
	if not doc.content_hash:
		try:
			content = doc.get_content()
			if content:
				doc.content_hash = hashlib.md5(content).hexdigest()
		except Exception:
			pass

	if not doc.content_hash:
		return

	# Check for existing files with same content hash across all uploads
	existing_files = frappe.get_all("File",
		filters={
			"content_hash": doc.content_hash,
		},
		fields=["name", "file_name", "attached_to_doctype", "attached_to_name"],
		limit=1
	)

	if existing_files:
		existing_file = existing_files[0]
		error_msg = "A file with identical content has already been uploaded"
		if existing_file.get("file_name"):
			error_msg += f" as \"{existing_file.get('file_name')}\""
		if existing_file.get("attached_to_name"):
			error_msg += f" (attached to {existing_file.get('attached_to_name')})"
		frappe.throw(_(error_msg + ". Please upload a different file."))


def on_update_file(doc, method):
	"""
	Rename file to libraryName@version.ext format when attached to Service Extension
	"""
	if doc.attached_to_doctype != "Service Extension" or not doc.attached_to_name:
		return

	# Get Service Extension document
	try:
		service_extension = frappe.get_doc("Service Extension", doc.attached_to_name)
	except:
		return

	# Only rename the file attached to the 'file' field, not other attachments
	if service_extension.file != doc.file_url:
		return

	# Check if we need to rename
	if not service_extension.library_name:
		return

	# Get file extension
	_, ext = os.path.splitext(doc.file_url)

	# Create new filename: libraryName@version.ext
	new_filename = f"{service_extension.library_name}@{service_extension.major}.{service_extension.minor}{ext}"

	# Check if already renamed
	if doc.file_name == new_filename:
		return

	# Get current file path
	old_path = frappe.get_site_path(doc.file_url.lstrip('/'))

	# Create new file path
	file_dir = os.path.dirname(old_path)
	new_path = os.path.join(file_dir, new_filename)

	# Rename physical file
	if os.path.exists(old_path) and old_path != new_path:
		os.rename(old_path, new_path)

		# Update File document
		doc.file_name = new_filename
		doc.file_url = os.path.join(os.path.dirname(doc.file_url), new_filename)
		# Don't call save() here as we're already in on_update event
		frappe.db.set_value("File", doc.name, {
			"file_name": new_filename,
			"file_url": doc.file_url
		}, update_modified=False)

