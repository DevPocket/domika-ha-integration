import asyncio

from HA_Pusher import pusher as push
from HA_Pusher import confirm_events
from HA_Pusher.const import *

# ALEX_TOKEN = "12fad1ba8ee6ebded99279d3da37b672d85dcd6b2d9a48ca40f090243bdec2d5"
BMIKLE_TOKEN = "a6b3cc48d19783a2063431c62bcd54029c6166163f3d8422acf3261f9ce3630c"
EVENT_CONFIRMER = confirm_events.EventConfirmer()

TEST_DATA="""{"entity 1": {"att1": {"v:"value 1", "t": 12345},"att2": {"v:"value 2", "t": 54321}},"entity 2": {"some att": {"v:"some value", "t": 10000}}}"""

if __name__ == '__main__':
    # loop = asyncio.new_event_loop()
    pusher = push.Pusher("", True)
    pusher.send_notification_ios(IOS_SANDBOX_ENV, BMIKLE_TOKEN, TEST_DATA)
    # pusher.init_ios_notifier("/Users/bmikle/SourceCode/Domika/domika-ha-integration/HA_Pusher/key.p8", None, True)
    # bmikle_id = pusher.update_push_notification_token(None, "bmikle", BMIKLE_TOKEN, "ios", "sandbox")
    # pusher.resubscribe(bmikle_id, {"Entity 1": ["A", "B"], "Entity 2": ["X", "Y"]})
    # pusher.resubscribe_push(bmikle_id, {"Entity 1": ["A"], "Entity 2": ["Y"]})
    # # print(pusher.install_ids_for_event("Entity 1", {("A", "1"), ("B1", "2"), ("X1", "3")}))
    #
    # pusher.add_event("Entity 1", set({"A": "1", "B": "2", "C": "3", "D": "4"}.items()), "cont1", 100)
    # pusher.add_event("Entity 2", set({"X": "x", "Y": "y"}.items()), "cont2", 200)
    # EVENT_CONFIRMER.add_confirmation(bmikle_id,"cont2")
    # pusher.generate_push_notifications_ios(EVENT_CONFIRMER)
    # pusher.add_event("Entity 2", set({"X": "x", "Y": "y"}.items()), "cont2", 200)

    # print(EVENT_CONFIRMER)
