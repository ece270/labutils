#! /usr/bin/env python3
import sqlite3, os, sys
from datetime import datetime, timedelta

def read(queue_db):
    conn = sqlite3.connect(queue_db)
    cur = conn.cursor()
    print("table checkoff")
    print(list(cur.execute("SELECT * FROM checkoff")))
    print("table help")
    print(list(cur.execute("SELECT * FROM help")))
    print("table _user")
    print(list(cur.execute("SELECT * FROM _user")))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        for x in os.listdir():
            if x.endswith(".db"):
                print("Reading " + x + "...")
                read(x)
    elif os.path.exists(sys.argv[1]):
        read(sys.argv[1])