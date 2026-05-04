# Copyright (c) 2026, CloudGCS and contributors
# For license information, please see license.txt

import json
from collections import Counter, defaultdict
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document
from service_warehouse.pilot_marketplace.doctype.pilot_profile.pilot_profile import sync_total_flight_hours

if TYPE_CHECKING:
	from frappe.types import DF


class PilotFlight(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		aircraft_name: DF.Data
		flight_date: DF.Date
		flight_hours: DF.Duration
		pilot: DF.Link
		source_flight_id: DF.Data
		tenant: DF.Link
		tenant_name: DF.Data
	# end: auto-generated types

	def on_update(self):
		for profile_name in self._get_affected_profiles():
			sync_total_flight_hours(profile_name)

	def after_delete(self):
		sync_total_flight_hours(self.pilot)

	def _get_affected_profiles(self):
		affected_profiles = {self.pilot}
		previous_doc = self.get_doc_before_save()
		if previous_doc and previous_doc.pilot:
			affected_profiles.add(previous_doc.pilot)
		return {profile_name for profile_name in affected_profiles if profile_name}


def _to_float(value):
	try:
		return float(value or 0)
	except (TypeError, ValueError):
		return 0.0


def _duration_seconds_to_hours(value):
	return _to_float(value) / 3600


def _extract_coordinates(value):
	if not value:
		return None

	data = value
	if isinstance(value, str):
		try:
			data = json.loads(value)
		except json.JSONDecodeError:
			return None

	if isinstance(data, list) and data:
		data = data[0]

	if isinstance(data, dict) and data.get("type") == "FeatureCollection":
		features = data.get("features") or []
		if not features:
			return None
		data = features[0]

	if not isinstance(data, dict):
		return None

	geometry = data.get("geometry") or {}
	if geometry.get("type") != "Point":
		return None

	coordinates = geometry.get("coordinates") or []
	if len(coordinates) < 2:
		return None

	try:
		lng = float(coordinates[0])
		lat = float(coordinates[1])
	except (TypeError, ValueError):
		return None

	return {"lat": lat, "lng": lng}


@frappe.whitelist()
def get_my_pilot_workspace_data():
	profile = frappe.db.get_value(
		"Pilot Profile",
		{"user": frappe.session.user},
		["name", "pilot_id", "full_name", "email", "phone", "time_zone", "status"],
		as_dict=True,
	)

	if not profile:
		return {
			"profile": None,
			"stats": {},
			"tenant_breakdown": [],
			"recent_flights": [],
			"map_points": [],
			"message": "Pilot profile not found for the current user.",
		}

	flights = frappe.get_all(
		"Pilot Flight",
		filters={"pilot": profile.name},
		fields=[
			"name",
			"tenant",
			"tenant_name",
			"aircraft_name",
			"flight_hours",
			"flight_date",
			"location",
		],
		order_by="flight_date desc, modified desc",
		limit_page_length=1000,
	)

	total_flights = len(flights)
	total_flight_hours = 0.0
	tenant_stats = defaultdict(lambda: {"tenant": "", "flight_count": 0, "flight_hours": 0.0})
	tenant_aircraft_stats = defaultdict(lambda: defaultdict(float))
	aircraft_counter = Counter()
	map_points = []

	for flight in flights:
		tenant_label = flight.tenant_name or flight.tenant or "Unknown Tenant"
		hours = _duration_seconds_to_hours(flight.flight_hours)
		total_flight_hours += hours

		tenant_stats[tenant_label]["tenant"] = tenant_label
		tenant_stats[tenant_label]["flight_count"] += 1
		tenant_stats[tenant_label]["flight_hours"] += hours
		tenant_aircraft_stats[tenant_label][flight.aircraft_name or "Unknown Aircraft"] += hours

		if flight.aircraft_name:
			aircraft_counter[flight.aircraft_name] += 1

		coordinates = _extract_coordinates(flight.location)
		if coordinates:
			map_points.append(
				{
					"name": flight.name,
					"tenant": tenant_label,
					"aircraft_name": flight.aircraft_name,
					"flight_date": str(flight.flight_date) if flight.flight_date else None,
					"lat": coordinates["lat"],
					"lng": coordinates["lng"],
				}
			)

	tenant_breakdown = sorted(
		tenant_stats.values(),
		key=lambda row: (row["flight_count"], row["flight_hours"], row["tenant"]),
		reverse=True,
	)

	for row in tenant_breakdown:
		row["share"] = round((row["flight_count"] / total_flights) * 100, 1) if total_flights else 0
		row["flight_hours"] = round(row["flight_hours"], 1)

	tenant_aircraft_breakdown = []
	for tenant_row in tenant_breakdown:
		tenant_name = tenant_row["tenant"]
		aircraft_rows = sorted(
			(
				{
					"aircraft_name": aircraft_name,
					"flight_hours": round(hours, 1),
				}
				for aircraft_name, hours in tenant_aircraft_stats[tenant_name].items()
			),
			key=lambda row: (row["flight_hours"], row["aircraft_name"]),
			reverse=True,
		)
		tenant_aircraft_breakdown.append(
			{
				"tenant": tenant_name,
				"total_hours": tenant_row["flight_hours"],
				"aircraft": aircraft_rows[:8],
			}
		)

	recent_flights = []
	for flight in flights[:6]:
		recent_flights.append(
			{
				"name": flight.name,
				"tenant": flight.tenant_name or flight.tenant or "Unknown Tenant",
				"aircraft_name": flight.aircraft_name or "Unknown Aircraft",
				"flight_hours": round(_duration_seconds_to_hours(flight.flight_hours), 1),
				"flight_date": str(flight.flight_date) if flight.flight_date else None,
				"url": f"/app/pilot-flight/{frappe.utils.cstr(flight.name)}",
			}
		)

	latest_flight_date = recent_flights[0]["flight_date"] if recent_flights else None
	primary_aircraft = aircraft_counter.most_common(1)[0][0] if aircraft_counter else None

	return {
		"profile": {
			"name": profile.name,
			"pilot_id": profile.pilot_id,
			"full_name": profile.full_name,
			"email": profile.email,
			"phone": profile.phone,
			"time_zone": profile.time_zone,
			"status": profile.status,
			"url": f"/app/pilot-profile/{frappe.utils.cstr(profile.name)}",
			"flights_url": "/app/pilot-flight",
		},
		"stats": {
			"total_flights": total_flights,
			"total_flight_hours": round(total_flight_hours, 1),
			"tenant_count": len(tenant_breakdown),
			"mapped_location_count": len(map_points),
			"latest_flight_date": latest_flight_date,
			"primary_aircraft": primary_aircraft,
		},
		"tenant_breakdown": tenant_breakdown[:8],
		"tenant_aircraft_breakdown": tenant_aircraft_breakdown[:8],
		"recent_flights": recent_flights,
		"map_points": map_points,
	}
