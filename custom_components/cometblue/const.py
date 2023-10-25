"""Constants for Cometblue BLE thermostats."""

DOMAIN = "cometblue"
DEFAULT_NAME = "Eurotronic CometBlue"

CONF_DEVICE_NAME = "device_name"
CONF_DATETIME = "datetime"
CONF_SCHEDULE = "schedule"


CONF_MONDAY = "monday"
CONF_TUESDAY = "tuesday"
CONF_WEDNESDAY = "wednesday"
CONF_THURSDAY = "thursday"
CONF_FRIDAY = "friday"
CONF_SATURDAY = "saturday"
CONF_SUNDAY = "sunday"
CONF_DELETE = "delete"
CONF_START = "start"
CONF_END = "end"
CONF_TEMPERATURE = "temperature"

CONF_ALL_DAYS = {
    CONF_MONDAY,
    CONF_TUESDAY,
    CONF_WEDNESDAY,
    CONF_THURSDAY,
    CONF_FRIDAY,
    CONF_SATURDAY,
    CONF_SUNDAY,
}
