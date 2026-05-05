# Copyright (c) 2026, CloudGCS and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestPilotProfile(FrappeTestCase):
	def test_total_flight_hours_uses_duration_seconds_for_experiences(self):
		profile = self._make_profile(
			flight_experiences=[
				{"aircraft_type": "C172", "flight_hours": 1.5},
				{"aircraft_type": "PA-28", "flight_hours": 2.25},
			]
		)

		self.assertEqual(profile.total_flight_hours, 13500)

		profile.flight_experiences[0].flight_hours = 3
		profile.save()

		self.assertEqual(profile.total_flight_hours, 18900)

	def test_flight_experience_hours_are_rounded_to_two_decimals(self):
		profile = self._make_profile(
			flight_experiences=[
				{"aircraft_type": "C172", "flight_hours": 1.239},
			]
		)

		self.assertEqual(profile.flight_experiences[0].flight_hours, 1.24)
		self.assertEqual(profile.total_flight_hours, 4464)

	def _make_profile(self, flight_experiences=None):
		suffix = frappe.generate_hash(length=8)
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"pilot-profile-{suffix}@example.com",
				"first_name": f"Pilot {suffix}",
			}
		).insert(ignore_permissions=True)

		profile = frappe.get_doc(
			{
				"doctype": "Pilot Profile",
				"pilot_id": f"PILOT-{suffix.upper()}",
				"user": user.name,
				"status": "Active",
				"flight_experiences": flight_experiences or [],
			}
		).insert(ignore_permissions=True)

		return profile
