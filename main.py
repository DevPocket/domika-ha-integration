import asyncio

from HA_Pusher import pusher as push
from HA_Pusher import confirm_events
from HA_Pusher.const import *

# ALEX_TOKEN = "12fad1ba8ee6ebded99279d3da37b672d85dcd6b2d9a48ca40f090243bdec2d5"
BMIKLE_TOKEN = "df3d0b7a0becd4338494fd89126268fd491fa699318edea9cd44c96ef9aa3a7c"
EVENT_CONFIRMER = confirm_events.EventConfirmer()

TEST_DATA="""{"entity 1": {"att1": {"v":"value 1", "t": 12345},"att2": {"v":"value 2", "t": 54321}},"entity 2": {"some att": {"v":"some value", "t": 10000}}}"""

def test_dashboards(pusher: push.Pusher):
    pusher.save_dashboards("user1", '{"dashboard1":"test"}')
    print(f'user1: {pusher.get_dashboards("user1")}')
    pusher.save_dashboards("user1", '{"dashboard1_1":"test1"}')
    print(f'user1: {pusher.get_dashboards("user1")}')
    print(f'user2: {pusher.get_dashboards("user2")}')

def test_send_notification_ios(pusher: push.Pusher):
    pusher.send_notification_ios(IOS_SANDBOX_ENV, BMIKLE_TOKEN, TEST_DATA, True)

def test_init(pusher: push.Pusher):
    bmikle_id = pusher.update_app_session_id("94673325-0591-4485-aa2e-aa64e7a473d3")
    print(bmikle_id)
    bmikle_id = pusher.update_push_notification_token(bmikle_id, BMIKLE_TOKEN, IOS_PLATFORM, IOS_SANDBOX_ENV)
    print(bmikle_id)
    bmikle_id = pusher.update_push_notification_token(None, BMIKLE_TOKEN, IOS_PLATFORM, IOS_SANDBOX_ENV)
    print(bmikle_id)

def test_events(pusher: push.Pusher):
    bmikle_id = pusher.update_app_session_id(None)
    pusher.resubscribe(bmikle_id, {"Entity 1": ["A", "B"], "Entity 2": ["X", "Y", "Z"]})
    pusher.resubscribe_push(bmikle_id, {"Entity 1": ["A"], "Entity 2": ["X", "Y"]})
    print(pusher.push_attributes_for_app_session_id(bmikle_id))
    print(pusher.app_session_ids_for_event("Entity 1", {("A", "1"), ("B1", "2"), ("X1", "3")}))

    pusher.add_event("Entity 1", set({"A": "1", "B": "2", "C": "3", "D": "4"}.items()), "cont1", 100)
    pusher.add_event("Entity 2", set({"X": "x", "Y": "y"}.items()), "cont2", 200)
    EVENT_CONFIRMER.add_confirmation(bmikle_id,"cont2")
    pusher.generate_push_notifications_ios(EVENT_CONFIRMER)
    pusher.add_event("Entity 2", set({"X": "x", "Y": "y"}.items()), "cont2", 200)
    print(EVENT_CONFIRMER)



if __name__ == '__main__':
    pusher = push.Pusher("", False)
    test_dashboards(pusher)
    test_init(pusher)
    test_events(pusher)

