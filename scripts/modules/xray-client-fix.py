#!/usr/bin/env python3
"""
FIX CLIENTI RELAZIONALI 3X-UI v3.6.0
Nelle nuove versioni di 3x-ui, i client non vengono più letti dal JSON settings della tabella inbounds,
ma devono essere inseriti obbligatoriamente nelle tabelle relazionali `clients` e `client_inbounds`.
Questo script inietta un client correttamente.
"""
import sqlite3
import uuid

DB_PATH = "/etc/x-ui/x-ui.db"

def add_client(inbound_id, email, client_uuid):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 1. Inserisci in clients
        c.execute("""
            INSERT OR IGNORE INTO clients (id, email, enable, up, down, expiry, total) 
            VALUES (?, ?, 1, 0, 0, 0, 0)
        """, (client_uuid, email))
        
        # 2. Collega in client_inbounds
        # L'ID in client_inbounds è tipicamente autoincrement o gestito diversamente, ma x-ui lo collega.
        c.execute("""
            INSERT OR IGNORE INTO client_inbounds (client_id, inbound_id)
            VALUES (?, ?)
        """, (client_uuid, inbound_id))
        
        conn.commit()
        print(f"Client {email} inserito correttamente nelle tabelle relazionali.")
    except Exception as e:
        print(f"Errore DB: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Esempio d'uso
    my_uuid = str(uuid.uuid4())
    print(f"Generato nuovo UUID: {my_uuid}")
    # add_client(1, "utente-mobile", my_uuid)
