import json
import pytz

from frappe.utils import get_system_timezone


def get_context(context):
    context.time_zone_options_json = json.dumps(pytz.all_timezones)
    context.default_time_zone = get_system_timezone()
    return context
