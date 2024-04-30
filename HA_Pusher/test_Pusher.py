from unittest import TestCase
from HA_Pusher import pusher


class TestPusher(TestCase):
    def test_init(self):
        # Recreate tables
        pusher = Pusher("test-", True)
        # Check that both tables are created
        res = pusher.cur.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?;", ["devices"])
        self.assertNotEqual(res.fetchone(), None)
        res = pusher.cur.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?;", ["subscriptions"])
        self.assertNotEqual(res.fetchone(), None)

        # Create test record
        id1 = pusher.create_push_notification_token("user 1", "token 1-1 ios", "ios", "test")
        # Check that the record exists
        res = pusher.cur.execute("SELECT 1 FROM devices WHERE user_id = ?;", ["user 1"])
        self.assertNotEqual(res.fetchone(), None)

        # Open db, do not recreate tables
        pusher = Pusher("test-")
        # Check that the record still exists
        res = pusher.cur.execute("SELECT 1 FROM devices WHERE user_id = ?;", ["user 1"])
        self.assertNotEqual(res.fetchone(), None)


    def test_create_push_notification_token(self):
        # Recreate tables
        pusher = Pusher("test-", True)

        # Create test records
        id1_1 = pusher.create_push_notification_token("user 1", "token 1-1 ios", "ios", "test")
        id1_2 = pusher.create_push_notification_token("user 1", "token 1-2 and", "android", "test")
        id2_1 = pusher.create_push_notification_token("user 2", "token 2-1 ios", "ios", "test")
        # Check that the record exists
        res = pusher.cur.execute("SELECT count(*) FROM devices WHERE user_id = ?;", ["user 1"])
        self.assertEqual(res.fetchone()[0], 2)
        res = pusher.cur.execute("SELECT count(*) FROM devices WHERE user_id = ?;", ["user 2"])
        self.assertEqual(res.fetchone()[0], 1)
        res = pusher.cur.execute("SELECT count(*) FROM devices WHERE user_id = ?;", ["user 3"])
        self.assertEqual(res.fetchone()[0], 0)

    def test_update_push_notification_token(self):
        # Recreate tables
        pusher = Pusher("test-", True)

        # Create test records
        id1_1 = pusher.create_push_notification_token("user 1", "token 1-1 ios", "ios", "test")
        id1_2 = pusher.create_push_notification_token("user 1", "token 1-2 and", "android", "test")
        id2_1 = pusher.create_push_notification_token("user 2", "token 2-1 ios", "ios", "test")
        pusher.update_push_notification_token(id1_2, "token 1-2 and UPDATE")

        # Check that the token updated exists
        res = pusher.cur.execute("SELECT token FROM devices WHERE install_id = ?;", [id1_2])
        self.assertEqual(res.fetchone()[0], "token 1-2 and UPDATE")

        # Try to create test record with empty token
        id0 = pusher.create_push_notification_token("user 1", "", "ios", "test")
        self.assertEqual(id0, "")


    def test_remove_push_notification_token(self):
        # Recreate tables
        pusher = Pusher("test-", True)

        # Create test records
        id1_1 = pusher.create_push_notification_token("user 1", "token 1-1 ios", "ios", "test")
        id1_2 = pusher.create_push_notification_token("user 1", "token 1-2 and", "android", "test")
        id2_1 = pusher.create_push_notification_token("user 2", "token 2-1 ios", "ios", "test")
        # Check that record exists
        res = pusher.cur.execute("SELECT count(*) FROM devices WHERE user_id = ?;", ["user 1"])
        self.assertEqual(res.fetchone()[0], 2)
        # Remove token 1_2
        pusher.remove_install_id(id1_2)
        # Check that record deleted
        res = pusher.cur.execute("SELECT count(*) FROM devices WHERE user_id = ?;", ["user 1"])
        self.assertEqual(res.fetchone()[0], 1)


    def test_update_subscriptions(self):
        # Recreate tables
        pusher = Pusher("test-", True)

        # Create test records
        id1_1 = pusher.create_push_notification_token("user 1", "token 1-1 ios", "ios", "test")
        id1_2 = pusher.create_push_notification_token("user 1", "token 1-2 and", "android", "test")

        pusher.add_subscriptions(id1_1, "Entity 1", ["att1_1", "att1_2", "att1_3"])
        pusher.add_subscriptions(id1_1, "Entity 1", ["att1_1", "att1_2", "att1_4"])
        pusher.add_subscriptions(id1_1, "Entity 2", ["att2_1", "att2_2"])

        # Check records
        res = pusher.cur.execute("SELECT * FROM subscriptions WHERE install_id = ?;", [id1_1])
        self.assertEqual(set(res.fetchall()), set([(id1_1, "Entity 1", "att1_1"), (id1_1, "Entity 1", "att1_2"), (id1_1, "Entity 1", "att1_3"), (id1_1, "Entity 1", "att1_4"), (id1_1, "Entity 2", "att2_1"), (id1_1, "Entity 2", "att2_2")]))

        # Update data
        pusher.remove_subscriptions(id1_1, "Entity 2")
        res = pusher.cur.execute("SELECT * FROM subscriptions WHERE install_id = ?;", [id1_1])
        self.assertEqual(set(res.fetchall()), set([(id1_1, "Entity 1", "att1_1"), (id1_1, "Entity 1", "att1_2"), (id1_1, "Entity 1", "att1_3"), (id1_1, "Entity 1", "att1_4")]))
        pusher.remove_subscriptions(id1_1)
        res = pusher.cur.execute("SELECT * FROM subscriptions WHERE install_id = ?;", [id1_1])
        self.assertEqual(res.fetchone(), None)


    def test_subscriptions_constraints(self):
        # Recreate tables
        pusher = Pusher("test-", True)

        # Create test records
        id1_1 = pusher.create_push_notification_token("user 1", "token 1-1 ios", "ios", "test")
        pusher.add_subscriptions("DUMMY ID", "Entity 1", ["att1_1", "att1_2", "att1_3"])
        # Check records
        res = pusher.cur.execute("SELECT * FROM subscriptions;")
        self.assertEqual(res.fetchone(), None)


    def test_remove_cascade(self):
        # Recreate tables
        pusher = Pusher("test-", True)

        # Create test records
        id1_1 = pusher.create_push_notification_token("user 1", "token 1-1 ios", "ios", "test")
        pusher.add_subscriptions(id1_1, "Entity 1", ["att1_1", "att1_2", "att1_3"])
        # Check records
        res = pusher.cur.execute("SELECT count(*) FROM subscriptions;")
        self.assertEqual(res.fetchone()[0], 3)

        # Remove install_id record
        pusher.remove_install_id(id1_1)
        # Check records
        res = pusher.cur.execute("SELECT count(*) FROM subscriptions;")
        self.assertEqual(res.fetchone()[0], 0)


    def test_process_event(self):
        # Recreate tables
        pusher = Pusher("test-", True)

        # Create and check test records
        # Insert {"A" : "1", "B" : "2"} with timestamp = 100
        pusher.add_event("1", {"C": "3", "Z": "100"}, {"A": "1", "B": "2", "C": "3"}, 100)
        res = pusher.cur.execute("SELECT count(*) FROM events;")
        self.assertEqual(res.fetchone()[0], 2)

        # Update {"A" : "11", "B" : "21"}
        pusher.add_event("1", {}, {"A": "11", "B": "21"}, 110)
        res = pusher.cur.execute("SELECT * FROM events;")
        self.assertEqual(set(res.fetchall()), set([("1", "A", "11", 110), ("1", "B", "21", 110)]))

        # Add {"C" : "3"}
        pusher.add_event("1", {}, {"A": "100", "B": "200", "C": "3"}, 90)
        res = pusher.cur.execute("SELECT * FROM events;")
        self.assertEqual(set(res.fetchall()), set([("1", "A", "11", 110), ("1", "B", "21", 110), ("1", "C", "3", 90)]))
