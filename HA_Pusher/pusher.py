# Pusher
from . import push_logger
from .const import *

import sqlite3
import traceback
import sys
from uuid import uuid4
import json
import requests
import threading

LOCK_ALL = threading.Lock()
TOKENS_TO_DELETE = set()

CURRENT_DB_VERSION: int = 11

# TBD: How to subscribe to certain events for all installations? Right now it's impossible, as app_session_id works as a PK

class Pusher:
    db = None
    cur = None

    # By default, DB file will be created in current folder and named HA_Pusher.db
    # If you want to create in different place, pass string in format: "file:/Users/alex/DB_Folder/"
    def __init__(self, database_path="", recreate_db=False):
        with LOCK_ALL:
            # Connect to db, if it does not exist — create one
            self.db = sqlite3.connect(database_path + EVENTS_DATABASE_NAME)
            self.db.row_factory = sqlite3.Row
            self.cur = self.db.cursor()
            self.cur.execute("PRAGMA foreign_keys = 1")
            self.create_db(recreate_db)
            self.update_db()


    def create_db(self, recreate_db):
        if recreate_db:
            # The order is important because of the foreign key in subscriptions
            self.cur.executescript("""
                DROP TABLE if exists push_data;
                DROP TABLE if exists events;
                DROP TABLE if exists subscriptions;
                DROP TABLE if exists devices;
                DROP TABLE if exists dashboards;
                DROP TABLE if exists db_version;
                """)

        self.cur.executescript("""
            CREATE TABLE if not exists db_version (
                version INTEGER NOT NULL DEFAULT 1 
                ); """)

        # If new tables (nothing in db_version) — set version to the latest
        if self.cur.execute("SELECT COUNT(*) FROM db_version").fetchone()[0] == 0:
            self.update_db_version()

        self.cur.executescript("""
            CREATE TABLE if not exists dashboards (
                user_id TEXT PRIMARY KEY NOT NULL, 
                dashboards TEXT NOT NULL 
                ); 

            CREATE TABLE if not exists devices (
                app_session_id TEXT PRIMARY KEY NOT NULL, 
                user_id TEXT NOT NULL, 
                push_session_id TEXT NOT NULL DEFAULT "", 
                token TEXT NOT NULL, 
                platform TEXT NOT NULL, 
                environment TEXT NOT NULL,
                last_update TEXT NOT NULL DEFAULT '2099-01-01 01:23:45'
                ); 

            CREATE TABLE if not exists subscriptions (
                app_session_id TEXT REFERENCES devices(app_session_id) ON UPDATE CASCADE ON DELETE CASCADE,
                entity_id TEXT NOT NULL,
                attribute TEXT NOT NULL,
                need_push INTEGER NOT NULL,
                UNIQUE(app_session_id, entity_id, attribute)
                ); 

            CREATE TABLE if not exists events (
                event_id TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                attribute TEXT NOT NULL,
                value TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                UNIQUE(entity_id, attribute)
                ); 

            CREATE TABLE if not exists push_data (
                app_session_id TEXT NOT NULL,
                push_session_id TEXT NOT NULL,
                token TEXT NOT NULL, 
                platform TEXT NOT NULL, 
                environment TEXT NOT NULL,
                event_id TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                attribute TEXT NOT NULL,
                value TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                UNIQUE(token, entity_id, attribute)
                ); 
                """)


    def update_db_version(self):
        self.cur.execute("DELETE FROM db_version;")
        self.cur.execute("INSERT INTO db_version (version) VALUES (?);", [CURRENT_DB_VERSION])
        self.db.commit()


    def update_db(self):
        def update_db_1_2():
            self.cur.executescript("""
            """)

        res = self.cur.execute("SELECT MAX(version) FROM db_version;")
        db_version = int(res.fetchone()[0]) or 1
        if db_version < CURRENT_DB_VERSION:
            push_logger.log_debug(f"recreating DB: user_version {db_version}, CURRENT_DB_VERSION {CURRENT_DB_VERSION}")
            self.create_db(True)
            # try:
            #     if db_version < 2:
            #         update_db_1_2()
            #     self.update_db_version()
            # except sqlite3.Error as er:
            #     push_logger.log_error(f"SQLite traceback: {traceback.format_exception(*sys.exc_info())}")


    def close_connection(self):
        self.db.close()


    def update_app_session_id(self, app_session_id, user_id) -> str:
        push_logger.log_debug(f"update_app_session_id, app_session_id={app_session_id}, user_id={user_id}")
        with LOCK_ALL:
            # Try to find the proper record. If no app_session_id found — generate a new one.
            res = self.cur.execute("""
                SELECT app_session_id
                FROM devices
                WHERE app_session_id = ? AND
                      user_id = ?
                ;""", [app_session_id, user_id])

            data = res.fetchall()
            if len(data) == 1:
                # Found a proper record. Update last_update field.
                row = data[0]
                self.cur.execute("""
                    UPDATE devices
                    SET last_update = datetime('now')
                    WHERE app_session_id = ?
                    ;""", [app_session_id])
                self.db.commit()
                return app_session_id
            else:
                # If we didn't find the right app_session_id we need to generate one
                success = False
                new_app_session_id = str(uuid4())
                while not success:
                    res = self.cur.execute("""SELECT count(*) FROM devices WHERE app_session_id = ? """,[new_app_session_id])
                    if res.fetchone()[0] == 0:
                        success = True
                    else:
                        new_app_session_id = str(uuid4())

                try:
                    self.cur.execute("""
                        INSERT INTO devices (app_session_id, user_id, token, platform, environment, last_update) 
                        VALUES (?, ?, "", "", "", datetime('now'))
                        ;""", [new_app_session_id, user_id])
                    self.db.commit()
                    return new_app_session_id
                except sqlite3.Error as er:
                    push_logger.log_error(f"SQLite traceback: {traceback.format_exception(*sys.exc_info())}")


    # Returns 2 if app_session_id exists, push_session_id exists and confirmed on the server, but the token is different
    # Returns 1 if success
    # Returns 0 if app_session_id exists, but token can't be activated or push_session_id does not exist
    # Returns -1 if app_session_id does not exist
    async def update_push_notification_token(self, app_session_id, user_id, token, platform, environment, hass=None) -> int:
        push_logger.log_debug(f"update_push_notification_token, app_session_id={app_session_id}, user_id={user_id}, token={token}, platform={platform}, environment={environment}")
        if not user_id or not token or not platform or not environment:
            push_logger.log_error(f"update_push_notification_token: one of the fields is empty, no record was updated: user_id={user_id}, token={token}, platform: {platform}, environment: {environment} ")
        else:
            with LOCK_ALL:
                res = self.cur.execute("""
                    SELECT app_session_id, push_session_id 
                    FROM devices
                    WHERE app_session_id = ? AND
                          user_id = ?
                    ;""", [app_session_id, user_id])

                data = res.fetchall()
                if len(data) == 1:
                    push_session_id = data[0][1]
                    if push_session_id:
                        payload = {"environment": environment, "token": token, "push_session_id": push_session_id, "platform": IOS_PLATFORM}
                        if not hass:
                            r = requests.post('https://domika.app/check_push_session',
                                              json=payload)
                        else:
                            r = await hass.async_add_executor_job(make_post_request,
                                                                  "https://domika.app/update_push_session",
                                                                  payload)
                        push_logger.log_debug(f"check_push_session result: {r.text}, {r.status_code}")
                        if r.text == "1":
                            # We don't want to store token in the integration in the future,
                            # it's a temp solution until we have a working push server
                            self.cur.execute("""
                                UPDATE devices
                                SET token = ?,
                                    platform = ?,
                                    environment = ?,
                                    last_update = datetime('now')
                                WHERE app_session_id = ?
                                ;""", [token, platform, environment, app_session_id])
                            self.db.commit()
                            return 1
                        elif r.text == "2":
                            return 2
                        else:
                            return 0
                    else:
                        return 0
                else:
                    # Wrong app_session_id
                    return -1


    def remove_app_session_id(self, app_session_id):
        push_logger.log_debug(f"remove_app_session_id, app_session_id={app_session_id}")
        if not app_session_id:
            push_logger.log_error(f"remove_app_session_id: app_session_id is empty, no record was removed: app_session_id: {app_session_id} ")
        else:
            self.cur.execute("DELETE FROM devices WHERE app_session_id = ?;", [app_session_id])
            self.db.commit()


    def save_push_session(self, app_session_id, push_session_id):
        push_logger.log_debug(f"save_push_session, app_session_id={app_session_id}, push_session_id={push_session_id}")
        with LOCK_ALL:
            if not app_session_id:
                push_logger.log_error(f"save_push_session: one of the fields is empty, no record was updated: app_session_id: {app_session_id} ")
            else:
                self.cur.execute("""
                    UPDATE devices 
                    SET push_session_id = ?
                    WHERE app_session_id = ?
                    ;""", [push_session_id, app_session_id])
                self.db.commit()


    def get_push_session(self, app_session_id):
        push_logger.log_debug(f"get_push_session, app_session_id={app_session_id} ")
        with LOCK_ALL:
            if not app_session_id:
                push_logger.log_error(f"get_push_session: one of the fields is empty, no record was updated: app_session_id: {app_session_id} ")
            else:
                db_res = self.cur.execute("""
                    SELECT push_session_id 
                    FROM devices 
                    WHERE app_session_id = ?
                    ;""", [app_session_id])
                res = list(db_res.fetchall())
                if len(res) == 1:
                    return res[0][0]
                else:
                    return ""


    def resubscribe(self, app_session_id, subscriptions):
        push_logger.log_debug(f"resubscribe, app_session_id={app_session_id}, subscriptions={subscriptions}")
        with LOCK_ALL:
            if not app_session_id or not subscriptions:
                push_logger.log_error(f"resubscribe: one of the fields is empty, no record was updated: app_session_id: {app_session_id}, subscriptions={subscriptions} ")
            else:
                data = []
                for entity_id in subscriptions:
                    attributes = subscriptions.get(entity_id)
                    for att in attributes:
                        data.append((app_session_id, entity_id, att, 0))

                try:
                    self.cur.execute("DELETE FROM subscriptions WHERE app_session_id = ? ;", [app_session_id])
                    self.cur.executemany("""
                        INSERT INTO subscriptions (app_session_id, entity_id, attribute, need_push) 
                        VALUES (?, ?, ?, ?)
                        ;""", data)
                    self.cur.execute("UPDATE devices SET last_update = datetime('now') WHERE app_session_id = ? ;", [app_session_id])
                    self.db.commit()
                except sqlite3.Error as er:
                    push_logger.log_error(f"SQLite traceback: {traceback.format_exception(*sys.exc_info())}")


    def resubscribe_push(self, app_session_id, subscriptions):
        push_logger.log_debug(f"resubscribe_push, app_session_id={app_session_id}, subscriptions={subscriptions}")
        with LOCK_ALL:
            if not app_session_id or not subscriptions:
                push_logger.log_error(f"resubscribe_push: one of the fields is empty, no record was updated: app_session_id: {app_session_id}, subscriptions={subscriptions} ")
            else:
                self.cur.execute("""
                    UPDATE subscriptions
                    SET need_push = 0
                    ;""")

                data = []
                for entity_id in subscriptions:
                    attributes = subscriptions.get(entity_id)
                    for att in attributes:
                        data.append((app_session_id, entity_id, att))

                try:
                    self.cur.executemany("""
                        UPDATE subscriptions
                        SET need_push = 1
                        WHERE app_session_id = ? AND 
                              entity_id  = ? AND
                              attribute = ? 
                        ;""", data)
                    self.db.commit()
                except sqlite3.Error as er:
                    push_logger.log_error(f"SQLite traceback: {traceback.format_exception(*sys.exc_info())}")


    def app_session_ids_for_event(self, entity_id: str, attributes: set) -> list:
        push_logger.log_debug(f"app_session_ids_for_event, entity_id={entity_id}, attributes={attributes}")
        with LOCK_ALL:
            if not entity_id or not attributes:
                push_logger.log_error(f"app_session_ids_for_event: one of the fields is empty, no record was updated: entity_id={entity_id}, attributes={attributes} ")
            else:
                atts = dict(attributes)
                json_atts = json.dumps(atts)
                try:
                    # self.db.set_trace_callback(print)
                    db_res = self.cur.execute(f"""
                        SELECT DISTINCT app_session_id
                        FROM subscriptions s
                        JOIN (SELECT key FROM json_each(?)) atts 
                            ON s.attribute = atts.key 
                        WHERE entity_id = ?
                        ;""", [json_atts, entity_id])
                    return [row[0] for row in db_res.fetchall()]
                except sqlite3.Error as er:
                    push_logger.log_error(f"SQLite traceback: {traceback.format_exception(*sys.exc_info())}")


    # Fetches the list of entites and their attributes this app_session_id is subscribed to (only those with need_push = 1)
    def push_attributes_for_app_session_id(self, app_session_id: str) -> list:
        push_logger.log_debug(f"push_attributes_for_app_session_id, app_session_id={app_session_id}")
        with LOCK_ALL:
            entities_list = []
            if not app_session_id:
                push_logger.log_error(f"push_attributes_for_app_session_id: app_session_id cannot be empty ")
            else:
                db_res = self.cur.execute(f"""
                    SELECT entity_id, attribute
                    FROM subscriptions s
                    WHERE app_session_id = ? AND
                          need_push = 1
                    ORDER BY entity_id
                    ;""", [app_session_id])

                last_entity_id = None
                entity_attributes = []
                for row in db_res.fetchall():
                    entity_id = row["entity_id"]
                    if entity_id != last_entity_id:
                        if entity_attributes:
                            entities_list.append({"entity_id": last_entity_id, "attributes": entity_attributes})
                        entity_attributes = []
                        last_entity_id = entity_id
                    entity_attributes.append(row["attribute"])
                if entity_attributes:
                    entities_list.append({"entity_id": last_entity_id, "attributes": entity_attributes})
            return entities_list


    def add_event(self, entity_id, attributes, event_id, timestamp):
        def remove_tokens_to_delete():
            global TOKENS_TO_DELETE
            tokens = TOKENS_TO_DELETE.copy()
            TOKENS_TO_DELETE -= tokens

            try:
                for token in tokens:
                    push_logger.log_debug(f"remove_tokens_to_delete: removing token: {token}")
                    self.cur.execute("""
                        DELETE FROM devices
                        WHERE token = ?
                        ;""", [token])
                self.db.commit()
                push_logger.log_debug(f"remove_tokens_to_delete: removed tokens: {tokens}")
            except sqlite3.Error as er:
                push_logger.log_error(f"SQLite traceback: {traceback.format_exception(*sys.exc_info())}")

        push_logger.log_debug(f"add_event, entity_id={entity_id}, attributes={attributes}, event_id={event_id}, timestamp={timestamp}")
        # Remove all tokens which were marked as bad
        remove_tokens_to_delete()

        if not entity_id or not attributes or not timestamp or not event_id:
            push_logger.log_error(f"add_event: one of the fields is empty, no record was updated: entity_id={entity_id}, attributes={attributes}, event_id={event_id}, timestamp={timestamp} ")
        else:
            with LOCK_ALL:
                data = []
                for element in attributes:
                    data.append((entity_id, element[0], element[1], event_id, timestamp))

                try:
                    self.cur.executemany("""
                        INSERT INTO events (entity_id, attribute, value, event_id, timestamp) 
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(entity_id, attribute) DO UPDATE SET
                            value = excluded.value,
                            timestamp = excluded.timestamp
                        WHERE excluded.timestamp >= events.timestamp
                        ;""", data)
                    self.db.commit()
                    self.process_events()
                except sqlite3.Error as er:
                    push_logger.log_error(f"SQLite traceback: {traceback.format_exception(*sys.exc_info())}")


    def process_events(self):
        push_logger.log_debug(f"process_events")
        try:
            self.cur.execute("""
                INSERT INTO push_data (app_session_id, push_session_id, token, platform, environment, entity_id, attribute, value, event_id, timestamp) 
                    SELECT d.app_session_id, d.push_session_id, d.token, d.platform, d.environment, e.entity_id, e.attribute, e.value, e.event_id, e.timestamp 
                    FROM events e
                        JOIN subscriptions s ON
                            e.entity_id = s.entity_id AND
                            e.attribute = s.attribute
                        JOIN devices d ON
                            s.app_session_id = d.app_session_id
                    WHERE s.need_push = 1 AND 
                          d.token != '' AND
                          d.push_session_id != ''
                ON CONFLICT(token, entity_id, attribute) DO UPDATE 
                    SET value = excluded.value,
                        timestamp = excluded.timestamp
                    WHERE excluded.timestamp >= push_data.timestamp
                ;""")

            self.cur.execute("DELETE FROM events;")
            self.db.commit()
        except sqlite3.Error as er:
            push_logger.log_error(f"SQLite traceback: {traceback.format_exception(*sys.exc_info())}")

    def remove_old_app_session_ids(self):
        self.cur.execute("""
            DELETE FROM devices
            WHERE julianday('now') - julianday(last_update) > ?
            ;""", [DEVICE_EXPIRATION_TIME])
        self.db.commit()

    async def generate_push_notifications_ios(self, hass):
        push_logger.log_debug(f"generate_push_notifications_ios")
        with LOCK_ALL:
            try:
                # Remove all install ids which did not update themselves for a long time
                self.remove_old_app_session_ids()

                db_res = self.cur.execute("""
                    SELECT token, environment, entity_id, attribute, value, app_session_id, push_session_id, event_id, timestamp
                    FROM push_data
                    WHERE platform = ?
                    ORDER BY token, entity_id
                    ;""", [IOS_PLATFORM])
                res = list(db_res.fetchall())
                self.cur.execute("""
                    DELETE FROM push_data 
                    WHERE platform = ?
                    ;""", [IOS_PLATFORM])
                self.db.commit()

                data = ""
                current_token = None
                current_environment = None
                current_push_session_id = None
                current_entity_id = None
                for row in res:
                    # First row
                    if current_token is None:
                        current_token = row["token"]
                        current_environment = row["environment"]
                        current_push_session_id = row["push_session_id"]

                    # New token or too long — send push with data
                    if current_token != row["token"] or len(data) > 2000:
                        await self.send_notification_ios(current_push_session_id, current_environment, current_token, "{" + data[:-1] + "}}", hass)
                        data = ""
                        current_token = row["token"]
                        current_environment = row["environment"]
                        current_push_session_id = row["push_session_id"]
                        current_entity_id = None

                    # New entity_id — add its name
                    if current_entity_id != row["entity_id"]:
                        # If not the first entity_id — close the last one
                        if current_entity_id is not None:
                            data = data[:-1] + f'}},'
                        # Open the new one
                        data += f'"{row["entity_id"]}":{{'
                        current_entity_id = row["entity_id"]

                    # Add current attribute to data
                    data += f'"{row["attribute"]}":{{"v":"{row["value"]}","t":{row["timestamp"]}}},'
                if len(data) > 0:
                    await self.send_notification_ios(current_push_session_id, current_environment, current_token, "{" + data[:-1] + "}}", hass)
            except sqlite3.Error as er:
                push_logger.log_error(f"SQLite traceback: {traceback.format_exception(*sys.exc_info())}")


    async def send_notification_ios(self, push_session_id, environment, token, data, hass=None):
        push_logger.log_debug(f"send_notification_ios, environment: {environment}, token: {token}, data: {data}")
        url = 'https://domika.app/send_notification'
        #     url = 'http://127.0.0.1:5000/send_notification'

        payload = {"push_session_id": push_session_id, "environment": environment, "token": token, "data": data, "platform": IOS_PLATFORM}
        if not hass:
            r = requests.post(url, json=payload)
        else:
            r = await hass.async_add_executor_job(make_post_request, url, payload)
        push_logger.log_debug(f"send_notification_ios result: {r.text}, {r.status_code}")

        if r.status_code == 422:
            TOKENS_TO_DELETE.add(token)


    def app_session_ids_for_user_id(self, user_id) -> list:
        with LOCK_ALL:
            if not user_id:
                push_logger.log_error(f"app_session_ids_for_user_id: user_id is empty: {user_id} ")
                return []
            else:
                db_res = self.cur.execute("""
                    SELECT app_session_id
                    FROM devices 
                    WHERE user_id = ?
                    ;""", [user_id])
                res = [item[0] for item in db_res.fetchall()]
                push_logger.log_debug(f"app_session_ids_for_user_id: res: {res} ")
                return res


    def save_dashboards(self, user_id: str, dashboards: str):
        with LOCK_ALL:
            if not user_id or not dashboards:
                push_logger.log_error(f"save_dashboards: one of the fields is empty, no record was updated: user_id: {user_id}, dashboards={dashboards} ")
            else:
                self.cur.execute("""
                    INSERT INTO dashboards (user_id, dashboards) 
                    VALUES (?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        dashboards = excluded.dashboards
                    ;""", [user_id, dashboards])
                self.db.commit()

    def get_dashboards(self, user_id: str) -> str:
        with LOCK_ALL:
            if not user_id:
                push_logger.log_error(f"get_dashboards: one of the fields is empty, no record was updated: user_id: {user_id} ")
            else:
                db_res = self.cur.execute("""
                    SELECT dashboards 
                    FROM dashboards 
                    WHERE user_id = ?
                    ;""", [user_id])
                res = list(db_res.fetchall())
                if len(res) == 1:
                    return res[0][0]
                else:
                    return ""

    def confirm_events(self, app_session_id: str, event_ids: list[str]):
        with LOCK_ALL:
            if not app_session_id or not event_ids:
                push_logger.log_error(f"confirm_events: one of the fields is empty, no record was updated: app_session_id: {app_session_id}, event_ids={event_ids} ")
            else:
                data = []
                for event_id in event_ids:
                    data.append( (app_session_id, event_id) )
                print(data)

                self.cur.executemany("""
                    DELETE FROM push_data
                    WHERE app_session_id = ? AND
                          event_id = ?
                ;""", data)
                self.db.commit()


def make_post_request(url, json_payload):
    return requests.request("post", url, json=json_payload, headers={"Content-Type": "application/json"})
