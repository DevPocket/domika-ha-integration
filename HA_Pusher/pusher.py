# Pusher
from homeassistant.core import callback

from . import push_logger
from .confirm_events import *
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

CURRENT_DB_VERSION: int = 2

# TBD: How to subscribe to certain events for all installations? Right now it's impossible, as install_id works as a PK

class Pusher:
    db = None
    cur = None

    # By default, DB file will be created in current folder and named HA_Pusher.db
    # If you want to create in different place, pass string in format: "file:/Users/alex/DB_Folder/"
    def __init__(self, database_path="", recreate_db=False):
        with LOCK_ALL:
            # Connect to db, if it does not exist — create one
            self.db = sqlite3.connect(database_path + SUBSCRIPTIONS_DATABASE_NAME)
            self.db.row_factory = sqlite3.Row
            self.cur = self.db.cursor()

            self.cur.execute("ATTACH DATABASE ? as EVENTS", (database_path + EVENTS_DATABASE_NAME, ))
            self.cur.execute("PRAGMA foreign_keys = 1")

            if recreate_db:
                # The order is important because of the foreign key in subscriptions
                self.cur.executescript("""
                    DROP TABLE if exists EVENTS.notifications;
                    DROP TABLE if exists EVENTS.push_data;
                    DROP TABLE if exists EVENTS.events;
                    DROP TABLE if exists subscriptions;
                    DROP TABLE if exists devices;
                    """)
                self.cur.execute(f"PRAGMA user_version = {CURRENT_DB_VERSION}")


            self.cur.executescript("""
                CREATE TABLE if not exists devices (
                    user_id TEXT NOT NULL, 
                    install_id TEXT PRIMARY KEY NOT NULL, 
                    token TEXT UNIQUE NOT NULL, 
                    platform TEXT NOT NULL, 
                    environment TEXT NOT NULL
                    ); 
                    
                CREATE TABLE if not exists subscriptions (
                    install_id TEXT REFERENCES devices(install_id) ON UPDATE CASCADE ON DELETE CASCADE,
                    entity_id TEXT NOT NULL,
                    attribute TEXT NOT NULL,
                    need_push INTEGER NOT NULL,
                    UNIQUE(install_id, entity_id, attribute)
                    ); 
                    
                CREATE TABLE if not exists EVENTS.events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    entity_id TEXT NOT NULL,
                    attribute TEXT NOT NULL,
                    value TEXT NOT NULL,
                    context_id TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    UNIQUE(entity_id, attribute)
                    ); 
                    
                CREATE TABLE if not exists EVENTS.push_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    install_id TEXT NOT NULL,
                    token TEXT NOT NULL, 
                    platform TEXT NOT NULL, 
                    environment TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    attribute TEXT NOT NULL,
                    value TEXT NOT NULL,
                    context_id TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    event_id INTEGER NOT NULL,
                    UNIQUE(token, entity_id, attribute)
                    ); 
                    
                CREATE TABLE if not exists EVENTS.notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    token TEXT NOT NULL, 
                    platform TEXT NOT NULL, 
                    environment TEXT NOT NULL,
                    data TEXT NOT NULL
                    ); 
                    """)
            self.update_db()


    def update_db(self):
        def update_db_1_2():
            self.cur.executescript("""
                ALTER TABLE subscriptions
                ADD COLUMN need_push INTEGER NOT NULL DEFAULT (0)
            """)

        res = self.cur.execute("PRAGMA user_version")
        db_version = int(res.fetchone()[0]) or 1
        if db_version < CURRENT_DB_VERSION:
            push_logger.log_debug(f"user_version: {db_version}, CURRENT_DB_VERSION: {CURRENT_DB_VERSION}")
            try:
                if db_version == 1:
                    update_db_1_2()
                self.cur.execute(f"PRAGMA user_version = {CURRENT_DB_VERSION}")
            except sqlite3.Error as er:
                push_logger.log_error(f"SQLite traceback: {traceback.format_exception(*sys.exc_info())}")


    def close_connection(self):
        self.db.close()


    def update_push_notification_token(self, install_id, user_id, token, platform, environment) -> str:
        def create_push_notification_token(self, user_id, token, platform, environment):
            push_logger.log_debug(f"create_push_notification_token, user_id={user_id}, token={token}, platform={platform}, environment={environment}")

            if not user_id or not token or not platform or not environment:
                push_logger.log_error(f"create_push_notification_token: one of the fields is empty, no record was created: user_id: {user_id}, token: {token}, platform: {platform}, environment: {environment} ")
            else:
                success = False
                new_install_id = str(uuid4())

                while not success:
                    res = self.cur.execute("""SELECT count(*) FROM devices WHERE install_id = ? """, [new_install_id])
                    if res.fetchone()[0] == 0:
                        success = True
                    else:
                        new_install_id = str(uuid4())

                try:
                    self.cur.execute("""
                        INSERT OR REPLACE INTO devices (user_id, install_id, token, platform, environment) 
                        VALUES (?, ?, ?, ?, ?)
                        ;""", [user_id, new_install_id, token, platform, environment])
                    self.db.commit()
                    return new_install_id
                except sqlite3.Error as er:
                    push_logger.log_error(f"SQLite traceback: {traceback.format_exception(*sys.exc_info())}")


        push_logger.log_debug(f"update_push_notification_token, install_id={install_id}, user_id={user_id}, token={token}, platform={platform}, environment={environment}")
        if not user_id or not token or not platform or not environment:
            push_logger.log_error(f"update_push_notification_token: one of the fields is empty, no record was updated: user_id: {user_id}, token: {token}, platform: {platform}, environment: {environment} ")
        else:
            with LOCK_ALL:
                res = self.cur.execute("""
                    SELECT install_id, user_id, token, platform, environment
                    FROM devices
                    WHERE install_id = ?
                    ;""", [install_id])

                data = res.fetchall()
                if len(data) == 1:
                    row = data[0]
                    if row[1] == user_id and row[3] == platform and row[4] == environment:
                        self.cur.execute("""
                            UPDATE devices
                            SET token = ?
                            WHERE install_id = ?
                            ;""", [token, install_id])
                        self.db.commit()
                        return install_id
                    else:
                        # push_logger.log_debug(f"update_push_notification_token, parameters sent differ from DB, recreating device record")
                        self.remove_push_notification_token(install_id)
                        return create_push_notification_token(self, user_id, token, platform, environment)
                else:
                    # push_logger.log_debug(f"update_push_notification_token, device not found, creating device record")
                    return create_push_notification_token(self, user_id, token, platform, environment)


    def remove_push_notification_token(self, install_id):
        push_logger.log_debug(f"remove_push_notification_token, install_id={install_id}")
        with LOCK_ALL:
            if not install_id:
                push_logger.log_error(f"remove_push_notification_token: install_id is empty, no record was removed: install_id: {install_id} ")
            else:
                self.cur.execute("DELETE FROM devices WHERE install_id = ?;", [install_id])
                self.db.commit()


    def resubscribe(self, install_id, subscriptions):
        push_logger.log_debug(f"resubscribe, install_id={install_id}, subscriptions={subscriptions}")
        with LOCK_ALL:
            if not install_id or not subscriptions:
                push_logger.log_error(f"resubscribe: one of the fields is empty, no record was updated: install_id: {install_id}, subscriptions={subscriptions} ")
            else:
                data = []
                for entity_id in subscriptions:
                    attributes = subscriptions.get(entity_id)
                    for att in attributes:
                        data.append((install_id, entity_id, att, 0))

                try:
                    self.cur.execute("DELETE FROM subscriptions WHERE install_id = ? ; ", [install_id])
                    self.cur.executemany("""
                        INSERT INTO subscriptions (install_id, entity_id, attribute, need_push) 
                        VALUES (?, ?, ?, ?)
                        ;""", data)
                    self.db.commit()
                except sqlite3.Error as er:
                    push_logger.log_error(f"SQLite traceback: {traceback.format_exception(*sys.exc_info())}")


    def resubscribe_push(self, install_id, subscriptions):
        push_logger.log_debug(f"resubscribe_push, install_id={install_id}, subscriptions={subscriptions}")
        with LOCK_ALL:
            if not install_id or not subscriptions:
                push_logger.log_error(f"resubscribe_push: one of the fields is empty, no record was updated: install_id: {install_id}, subscriptions={subscriptions} ")
            else:
                self.cur.execute("""
                    UPDATE subscriptions
                    SET need_push = 0
                    ;""")

                data = []
                for entity_id in subscriptions:
                    attributes = subscriptions.get(entity_id)
                    for att in attributes:
                        data.append((install_id, entity_id, att))

                try:
                    self.cur.executemany("""
                        UPDATE subscriptions
                        SET need_push = 1
                        WHERE install_id = ? AND 
                              entity_id  = ? AND
                              attribute = ? 
                        ;""", data)
                    self.db.commit()
                except sqlite3.Error as er:
                    push_logger.log_error(f"SQLite traceback: {traceback.format_exception(*sys.exc_info())}")


    def install_ids_for_event(self, entity_id: str, attributes: set) -> list:
        push_logger.log_debug(f"install_ids_for_event, entity_id={entity_id}, attributes={attributes}")
        with LOCK_ALL:
            if not entity_id or not attributes:
                push_logger.log_error(f"install_ids_for_event: one of the fields is empty, no record was updated: entity_id={entity_id}, attributes={attributes} ")
            else:
                atts = dict(attributes)
                json_atts = json.dumps(atts)
                try:
                    self.db.set_trace_callback(print)
                    db_res = self.cur.execute(f"""
                        SELECT DISTINCT install_id
                        FROM subscriptions s
                        JOIN (SELECT key FROM json_each(?)) atts 
                            ON s.attribute = atts.key 
                        WHERE entity_id = ?
                        ;""", [json_atts, entity_id])
                    return [row[0] for row in db_res.fetchall()]
                except sqlite3.Error as er:
                    push_logger.log_error(f"SQLite traceback: {traceback.format_exception(*sys.exc_info())}")


    def add_event(self, entity_id, attributes, context_id, timestamp):
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

        push_logger.log_debug(f"add_event, entity_id={entity_id}, attributes={attributes}, context_id={context_id}, timestamp={timestamp}")
        # Remove all tokens which were marked as bad
        remove_tokens_to_delete()

        if not entity_id or not attributes or not timestamp:
            push_logger.log_error(f"add_event: one of the fields is empty, no record was updated: entity_id: {entity_id}, attributes: {attributes}, timestamp: {timestamp} ")
        else:
            with LOCK_ALL:
                data = []
                for element in attributes:
                    data.append((entity_id, element[0], element[1], context_id or "", timestamp))

                try:
                    self.cur.executemany("""
                        INSERT INTO events (entity_id, attribute, value, context_id, timestamp) 
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
                INSERT INTO EVENTS.push_data (install_id, token, platform, environment, entity_id, attribute, value, context_id, timestamp, event_id) 
                    SELECT d.install_id, d.token, d.platform, d.environment, e.entity_id, e.attribute, e.value, e.context_id, e.timestamp, e.id 
                    FROM events e
                        JOIN subscriptions s ON
                            e.entity_id = s.entity_id AND
                            e.attribute = s.attribute
                        JOIN devices d ON
                            s.install_id = d.install_id
                    WHERE s.need_push = 1
                ON CONFLICT(token, entity_id, attribute) DO UPDATE 
                    SET value = excluded.value,
                        timestamp = excluded.timestamp
                    WHERE excluded.timestamp >= push_data.timestamp
                ;""")

            self.cur.execute("DELETE FROM events;")
            self.db.commit()
        except sqlite3.Error as er:
            push_logger.log_error(f"SQLite traceback: {traceback.format_exception(*sys.exc_info())}")


    def generate_push_notifications_ios(self, event_confirmer: EventConfirmer):
        push_logger.log_debug(f"generate_push_notifications_ios, event_confirmer={event_confirmer}")
        with LOCK_ALL:
            try:
                db_res = self.cur.execute("""
                    SELECT id, token, environment, entity_id, attribute, value, install_id, context_id, timestamp
                    FROM EVENTS.push_data
                    WHERE platform = ?
                    ORDER BY token, entity_id
                    ;""", [IOS_PLATFORM])
                res = list(db_res.fetchall())
                self.cur.execute("""
                    DELETE FROM EVENTS.push_data 
                    WHERE platform = ?
                    ;""", [IOS_PLATFORM])
                self.db.commit()

                #             "entity 1": {
                #                 "att1": {"v:"value 1", "t": 12345},
                #                 "att2": {"v:"value 2", "t": 54321}
                #             },
                #             "entity 2": {
                #                 "some att": {"v:"some value", "t": 10000},
                #             }

                data = ""
                current_token = None
                current_environment = None
                current_entity_id = None
                for row in res:
                    # If already confirmed — skip
                    if event_confirmer.found_confirmation(row["install_id"], row["context_id"]):
                        push_logger.log_debug(f'found a row to skip: {row["install_id"]}, {row["context_id"]}')
                        continue
                    # First row
                    if current_token is None:
                        current_token = row["token"]
                        current_environment = row["environment"]

                    # New token or too long — send push with data
                    if current_token != row["token"] or len(data) > 2000:
                        self.send_notification_ios(current_environment, current_token, "{" + data[:-1] + "}}")
                        data = ""
                        current_token = row["token"]
                        current_environment = row["environment"]
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
                    # data += f'"{row["attribute"]}":"{row["value"]}",'
                    data += f""""{row["attribute"]}":{{"v":"{row["value"]}","t":{row["timestamp"]}}},"""
                if len(data) > 0:
                    self.send_notification_ios(current_environment, current_token, "{" + data[:-1] + "}}")
            except sqlite3.Error as er:
                push_logger.log_error(f"SQLite traceback: {traceback.format_exception(*sys.exc_info())}")

        # No matter what — remove expired.
        event_confirmer.remove_expired()

    def send_notification_ios(self, environment, token, data):
        push_logger.log_debug(f"send_notification_ios, environment: {environment}, token: {token}, data: {data}")
        r = requests.post('http://127.0.0.1:5000/add_notification_ios',
                          json={"environment": environment, "token": token, "data": data})
        push_logger.log_debug(f"send_notification_ios result: {r.status_code}")


    # def send_push_notifications_ios_callback(self, token: str, status: str):
    #     push_logger.log_debug(f"send_push_notifications_ios_callback, token: {token}, status: {status}")
    #     if status == "410":
    #         TOKENS_TO_DELETE.add(token)
