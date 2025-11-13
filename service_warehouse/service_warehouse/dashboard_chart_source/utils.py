import frappe
from frappe.utils import getdate, nowdate, add_to_date
from frappe.utils.dateutils import get_from_date_from_timespan, get_period_ending, get_period, get_period_beginning

def fetch_chart_series_data(doctype, serie_field, date_field="creation", aggregation_field="COUNT(*)", timegrain="Monthly", filters=None):
    interval_field = get_timegrain_field(date_field, timegrain)
    # Query data using frappe.db.get_list
    data = frappe.db.get_list(
        doctype,
        fields=[
            f"{serie_field} as serie_name",
            f"{date_field} as min_date",
            f"{aggregation_field} as value"
        ],
        filters=filters,
        group_by=f"{interval_field}, serie_name",
        order_by=f"{interval_field} ASC, serie_name ASC",
        as_list=False
    )
    return data

def handle_chart_parameters(chart_name, chart, filters, from_date, to_date, timespan, time_interval):
    if chart_name:
        chart = frappe.get_doc("Dashboard Chart", chart_name)
    else:
        chart = frappe._dict(frappe.parse_json(chart) or {})

    # Merge filters
    filters = chart.filters_json or filters or {}
    filters = frappe.parse_json(filters) if isinstance(filters, str) else filters

    timespan = timespan or chart.timespan
    time_interval = time_interval or chart.time_interval or "Monthly"
    from_date, to_date = handle_timespan(chart, timespan, from_date, to_date)
    periods = create_periods(from_date, to_date, time_interval)
    aggregation = filters.get("aggregation", "Count")  # Default aggregation
    return (chart, filters, from_date, to_date, timespan, time_interval, periods, aggregation)

def handle_timespan(chart, timespan, from_date, to_date):
    if timespan == "Select Date Range":
        from_date = getdate(from_date or chart.from_date)
        to_date = getdate(to_date or chart.to_date) or nowdate()
    else:
        to_date = add_to_date(nowdate(),days=1) # include all times today
        from_date = get_from_date_from_timespan(to_date, timespan)
    return from_date, to_date

def create_periods(from_date, to_date, timegrain):
    dates = get_dates_from_timegrain(from_date, to_date, timegrain)
    return [get_period(get_period_beginning(date, timegrain), timegrain) for date in dates]

def get_timegrain_field(date_field, timegrain):
    formats = {
        "Daily": f"CAST({date_field} AS DATE)", # Use double % to escape it
        "Weekly": f"YEARWEEK({date_field})", # Use double % to escape it
        "Monthly": f"YEAR({date_field}), MONTH({date_field})", # Use double % to escape it
        "Quarterly": f"YEAR({date_field}), QUARTER({date_field})",
        "Yearly": f"YEAR({date_field})"
    }
    field = formats.get(timegrain)
    if not field: frappe.throw(f"Invalid interval: {timegrain}")
    return field

def get_dates_from_timegrain(from_date, to_date, timegrain):
    days = months = years = 0
    if "Daily" == timegrain:
        days = 1
    elif "Weekly" == timegrain:
        days = 7
    elif "Monthly" == timegrain:
        months = 1
    elif "Quarterly" == timegrain:
        months = 3
    else:
        months = 12

    dates = [get_period_ending(from_date, timegrain)]
    while getdate(dates[-1]) < getdate(to_date):
        date = get_period_ending(add_to_date(dates[-1], years=years, months=months, days=days), timegrain)
        dates.append(date)
    return dates

def format_chart_data_with_periods(data, periods, timegrain):
    # Format data for chart with all periods included
    result = {}

    # Initialize the result dictionary with all serie_names and all periods
    for row in data:
        serie_name = row["serie_name"]
        result.setdefault(serie_name, {period: 0 for period in periods})

    # Populate the result dictionary with actual data
    for row in data:
        serie_name = row["serie_name"]
        period_beginning = get_period_beginning(row["min_date"], timegrain)
        period = get_period(period_beginning, timegrain)
        value = row["value"]
        result[serie_name][period] = value

    # Convert into chart-friendly format
    datasets = [{"name": serie_name, "values": [entries[period] for period in periods]} for serie_name, entries in result.items()]

    return {
        "labels": periods,
        "datasets": datasets,
        "message": { "raw_data": data, "result": result }
    }
