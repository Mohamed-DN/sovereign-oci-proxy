#!/usr/bin/env python3
"""
3X-UI v3.6.0 RELATIONAL CLIENTS FIX
In newer versions of 3x-ui, clients are no longer read from the JSON settings.
They MUST be inserted into the relational `clients` and `client_inbounds` tables.
This script injects a client correctly into the database to avoid silent drops.
"""
import sqlite3
import uuid

DB_PATH = "/etc/x-ui/x-ui.db"

def add_client(inbound_id, email, client_uuid):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 1. Insert into clients
        c.execute("""
            INSERT OR IGNORE INTO clients (id, email, enable, up, down, expiry, total) 
            VALUES (?, ?, 1, 0, 0, 0, 0)
        """, (client_uuid, email))
        
        # 2. Link in client_inbounds
        c.execute("""
            INSERT OR IGNORE INTO client_inbounds (client_id, inbound_id)
            VALUES (?, ?)
        """, (client_uuid, inbound_id))
        
        conn.commit()
        print(f"Client {email} successfully inserted into relational tables.")
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    my_uuid = str(uuid.uuid4())
    print(f"Generated new UUID: {my_uuid}")
