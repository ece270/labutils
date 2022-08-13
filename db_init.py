#! /usr/bin/env python3
import sqlite3, os, sys
from datetime import datetime, timedelta

def reinit(queue_db):
    if os.path.exists(queue_db):
        os.remove(queue_db)
    conn = sqlite3.connect(queue_db)
    cur = conn.cursor()
    cur.execute("CREATE TABLE checkoff (station INTEGER PRIMARY KEY, visible INTEGER DEFAULT 0, time REAL)")
    conn.commit()
    cur.execute("CREATE TABLE help (station INTEGER PRIMARY KEY, visible INTEGER DEFAULT 0, time REAL)")
    conn.commit()
    cur.execute("CREATE TABLE _user (id INTEGER primary key autoincrement, login char(8), station integer, time real not null)")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        for x in os.listdir():
            if x.endswith(".db"):
                print("Resetting " + x + "...")
                reinit(x)
    elif os.path.exists(sys.argv[1]):
        reinit(sys.argv[1])