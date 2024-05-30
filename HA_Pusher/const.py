EVENTS_DATABASE_NAME = "Pusher_events.db"

# Event confirmation records will stay at least 15 seconds
EVENT_CONFIRMATION_EXPIRATION_TIME = 15 * 1e6

IOS_PLATFORM = "ios"
IOS_SANDBOX_ENV = "sandbox"
IOS_PRODUCTION_ENV = "production"

ANDROID_PLATFORM = "android"

# Number of days
DEVICE_EXPIRATION_TIME = 15

MICHAELs_PUSH_SERVER = False
if MICHAELs_PUSH_SERVER:
    BASE_URL = "https://domika.app/"
else:
    BASE_URL = "http://159.203.109.27:8000/api/v1/"

#http://159.203.109.27:8000/api/v1/docs#/