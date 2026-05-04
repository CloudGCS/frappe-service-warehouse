# Copyright (c) 2026, CloudGCS and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from service_warehouse.pilot_marketplace.controller.pilot_controller import upsert_pilot_flight


class TestPilotFlight(FrappeTestCase):
	def test_pilot_flight_updates_profile_total_on_insert_update_and_delete(self):
		profile = self._make_profile(
			flight_experiences=[{"aircraft_type": "C172", "flight_hours": 1.0}]
		)

		flight = frappe.get_doc(
			{
				"doctype": "Pilot Flight",
				"pilot": profile.name,
				"tenant": self._get_tenant_name(),
				"aircraft_name": "C172",
				"flight_hours": 7200,
				"flight_date": "2026-05-04",
				"source_flight_id": f"FLIGHT-{frappe.generate_hash(length=8).upper()}",
				"location": self._get_location_payload(),
			}
		).insert(ignore_permissions=True)

		profile.reload()
		self.assertEqual(profile.total_flight_hours, 10800)

		flight.flight_hours = 5400
		flight.save(ignore_permissions=True)

		profile.reload()
		self.assertEqual(profile.total_flight_hours, 9000)

		flight.delete(ignore_permissions=True)

		profile.reload()
		self.assertEqual(profile.total_flight_hours, 3600)

	def test_upsert_pilot_flight_keeps_numeric_duration_seconds(self):
		profile = self._make_profile()
		source_flight_id = f"UPSERT-{frappe.generate_hash(length=8).upper()}"

		response = upsert_pilot_flight(
			pilot_id=profile.pilot_id,
			source_flight_id=source_flight_id,
			tenant_code=self._get_tenant_name(),
			aircraft_name="DA42",
			flight_hours=5400,
			flight_date="2026-05-04T09:30:00Z",
			location=self._get_location_payload(),
		)

		self.assertEqual(response.get("status"), "success")
		self.assertEqual(frappe.db.get_value("Pilot Flight", source_flight_id, "flight_hours"), 5400)

		profile.reload()
		self.assertEqual(profile.total_flight_hours, 5400)

	def _make_profile(self, flight_experiences=None):
		suffix = frappe.generate_hash(length=8)
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"pilot-flight-{suffix}@example.com",
				"first_name": f"Pilot {suffix}",
			}
		).insert(ignore_permissions=True)

		return frappe.get_doc(
			{
				"doctype": "Pilot Profile",
				"pilot_id": f"PILOT-{suffix.upper()}",
				"user": user.name,
				"status": "Active",
				"flight_experiences": flight_experiences or [],
			}
		).insert(ignore_permissions=True)

	def _get_tenant_name(self):
		tenant_name = frappe.db.exists("Tenant", "HOST")
		if tenant_name:
			return tenant_name

		suffix = frappe.generate_hash(length=8)
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"tenant-{suffix}@example.com",
				"first_name": f"Tenant {suffix}",
			}
		).insert(ignore_permissions=True)

		return frappe.get_doc(
			{
				"doctype": "Tenant",
				"tenant_code": f"TEN{suffix[:5].upper()}",
				"tenant_name": f"Tenant {suffix}",
				"user": user.name,
				"provider_code": f"PRV{suffix[:5].upper()}",
				"provider_title": f"Provider {suffix}",
			}
		).insert(ignore_permissions=True).name

	def _get_location_payload(self):
		return """{
  "type": "Feature",
  "properties": {},
  "geometry": {
    "type": "Point",
    "coordinates": [29.0, 41.0]
  }
}"""
