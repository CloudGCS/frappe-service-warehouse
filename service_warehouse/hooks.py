app_name = "service_warehouse"
app_title = "Service Warehouse"
app_publisher = "CloudGCS"
app_description = "An app that manages tenants and service marketplace"
app_email = "contact@cloudgcs.com"
app_license = "mit"
# required_apps = []



fixtures = [
  {"dt": "Service Extension Type", "filters": [["name", "in", ["PS Plugin", "MC Plugin", "Web Application", "Service Container"]]]},
  {"dt": "User", "filters": [["username", "in", ["host"]]]},
  {"dt": "Service Provider", "filters": [["name", "in", ["SYSTEM"]]]},
  {"dt": "Tenant", "filters": [["name", "in", ["HOST"]]]},
  {"dt": "Service Extension", "filters": [
                                          ["service_provider", "in", ["SYSTEM"]],
                                          ["extension_code", "not like", "%Test%"],
                                          ["extension_code", "not like", "%TEST%"]
                                        ]},
  {"dt": "Role", "filters": [["name", "in", ["Host", "Pilot Role"]]]},
  {"dt": "Role Profile", "filters": [["name", "in", ["Pilot"]]]},
  {"dt": "Module Profile", "filters": [["name", "in", ["Pilot"]]]},
  {"doctype": "Custom HTML Block"},

]


# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/service_warehouse/css/service_warehouse.css"
app_include_js = "/assets/service_warehouse/js/workspace_filter.js"

# include js, css files in header of web template
# web_include_css = "/assets/service_warehouse/css/service_warehouse.css"
# web_include_js = "/assets/service_warehouse/js/service_warehouse.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "service_warehouse/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "service_warehouse/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "service_warehouse.utils.jinja_methods",
# 	"filters": "service_warehouse.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "service_warehouse.install.before_install"
# after_install = "service_warehouse.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "service_warehouse.uninstall.before_uninstall"
# after_uninstall = "service_warehouse.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "service_warehouse.utils.before_app_install"
# after_app_install = "service_warehouse.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "service_warehouse.utils.before_app_uninstall"
# after_app_uninstall = "service_warehouse.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "service_warehouse.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"Service Packet": "service_warehouse.permissions.filter_service_packets",
  "Service Subscription": "service_warehouse.permissions.filter_service_subscriptions",
  "Pilot Profile": "service_warehouse.service_warehouse.controller.pilot_controller.get_pilot_profile_permission_query",
  "Pilot Flight Log": "service_warehouse.service_warehouse.controller.pilot_controller.get_pilot_flight_log_permission_query",
}
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "File": {
        "before_insert": "service_warehouse.overrides.file_override.validate_file",
        "after_insert": "service_warehouse.overrides.file_override.on_update_file",
    },
    "User": {
        "after_insert": "service_warehouse.service_warehouse.controller.pilot_controller.create_pilot_profile_if_pilot",
    },
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"service_warehouse.tasks.all"
# 	],
# 	"daily": [
# 		"service_warehouse.tasks.daily"
# 	],
# 	"hourly": [
# 		"service_warehouse.tasks.hourly"
# 	],
# 	"weekly": [
# 		"service_warehouse.tasks.weekly"
# 	],
# 	"monthly": [
# 		"service_warehouse.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "service_warehouse.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
    "get_user_boxes": "service_warehouse.service_warehouse.controller.server_box_controller.get_user_boxes",
    "update_server_box_info_data": "service_warehouse.service_warehouse.controller.server_box_controller.update_server_box_info_data",
    "get_pilot_by_pilot_id": "service_warehouse.service_warehouse.controller.pilot_controller.get_pilot_by_pilot_id",
    "register_pilot": "service_warehouse.service_warehouse.controller.pilot_controller.register_pilot",
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "service_warehouse.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["service_warehouse.utils.before_request"]
# after_request = ["service_warehouse.utils.after_request"]

# Job Events
# ----------
# before_job = ["service_warehouse.utils.before_job"]
# after_job = ["service_warehouse.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"service_warehouse.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }
