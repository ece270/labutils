#! /usr/bin/env python3
import os
import json
import cgi
import re
import sys
import sqlite3
import shutil
from mod_python import apache, util
from json import load
from time import time, sleep
from datetime import datetime, timedelta
from functools import reduce
import pyinotify

# predefined here so doexec will pass it to config.py script.
ip = None

def doexec(path):
    exec(compile(open(path).read(), path, "exec"), globals())

def timeinsection(time, section):
    now = datetime.now()
    matches = re.match(r'Section [0-9]+ - ([A-Za-z]+) ([^ ]+) to (.+)', section)
    day = matches.group(1)
    sectionS = datetime.strptime("%s-%s-%s %s %s" % (now.strftime("%Y"), now.strftime("%m"), now.strftime("%d"), day, matches.group(2)), "%Y-%m-%d %A %I:%M%p") - timedelta(minutes=5)
    sectionE = datetime.strptime("%s-%s-%s %s %s" % (now.strftime("%Y"), now.strftime("%m"), now.strftime("%d"), day, matches.group(3)), "%Y-%m-%d %A %I:%M%p") + timedelta(minutes=5)
    return sectionS < now and now < sectionE

def userinsection(user, section):
    # check if current week is having a virtual lab
    # in that case, we can ignore section-student constraints
    # by returning True for all students
    if isofficehoursweek():
        return True
    sectionnum = int(re.match(r'Section ([0-9]+) - [A-Za-z]+ [^-]+ to .+', section).group(1))
    return user in section_student[sectionnum]

def getqueues():
    conn = sqlite3.connect(queue_db)
    cur = conn.cursor()
    # get all queues, then get all queue data
    queues = {}
    with conn:
        names = [row[1] for row in cur.execute('SELECT * FROM sqlite_master') if not (row[1].startswith("_") or row[1].startswith("sqlite"))]
    for n in names:
        queues[n] = list(cur.execute("select distinct {0}.station, {0}.time from {0} join _user where {0}.station == _user.station and {0}.visible == 1 order by {0}.time".format(n)))
    conn.close()
    return queues

def acquireLock(path):
    t = 0
    while t < 5 and os.path.exists(path + ".lck"):
        sleep(1)
        t += 1
    if t == 5:
        raise Exception("lockdir " + path + ".lck" + " not removed.")
    try:
        os.mkdir(path + ".lck")
    except:
        raise Exception("Unable to create lockdir")
    return path + ".lck"

def releaseLock(lock):
    if os.path.exists(lock):
        try:
            shutil.rmtree(lock)
        except:
            raise Exception("Unable to remove lockdir")

def handler(req):
    global ip
    # initialize some variables
    user = req.user
    query = util.FieldStorage(req)
    ip = req.useragent_ip

    # then grab config based on IP and init all variables
    try:
        doexec(os.environ['HOME'] + "/private/labutils/config.py")
    except Exception as e:
        req.content_type = "text/plain"
        req.send_http_header()
        req.write(str(os.environ))        
        req.write(str(e))
        return apache.OK

    # and some variables require the config to be set first...
    is_staff = user in staff

    if not os.path.exists(queue_db):
        req.write("Failure to find database.")
        return apache.OK
    
    # action+queue parameter is required, and queue must be list of queues from database
    # for testing purposes, SSH into machine and do a cURL (which we should block when in production)
    queues = getqueues()
    section = getactivesection()
    class EventHandler(pyinotify.ProcessEvent):
        def process_IN_MODIFY(self, event):
            try:
                req.write("data: %s\n\r" % json.dumps(getqueues()))
            except:
                pass
    
    # now check our variables
    querychecked = 'action' in query and 'queue' in query and query.get('queue', None) in queues
    
    # set up sqlite connection for later
    conn = sqlite3.connect(queue_db)
    cur = conn.cursor()

    try:
        station = getstation(ip)
    except:
        # problem.  IP does not belong to lab stations
        req.content_type = "text/plain"
        req.send_http_header()
        req.write("You are not permitted to access this page outside of lab.\r\n")
        return apache.OK
    
    # this section handles adding and removing
    if querychecked and station:
        queue = query.get('queue', None)
        # queue name is already in database, so we can safely substitute it into SQL query
        db_queue = list(cur.execute("SELECT * FROM %s" % queue))
        
        # make sure user-station pair matches the one in the database if in lab section
        # this check is necessary to partially protect against scripting
        user_match = list(cur.execute("SELECT * FROM _user WHERE station = (?) and login = (?)", (station, user)))
        if len(user_match) == 0:
            conn.close()
            return apache.HTTP_FORBIDDEN
        
        # perform actions based on whether adding/deleting
        will_add = query.get('action', None) == 'add' and 0 in [x[1] for x in db_queue if x[0] == int(station)] # and should not be currently visible
        will_del = query.get('action', None) == 'del' and 1 in [x[1] for x in db_queue if x[0] == int(station)] # and should be currently visible
        # only make changes to database if changes are to be made
        if will_add or will_del:
            try:
                with conn:
                    if will_add:
                        cur.execute("UPDATE %s SET visible = 1, time = (?) WHERE station = (?)" % queue, (time(), station))
                        lock = acquireLock(private + room + ".log")
                        with open(private + room + ".log", "a+") as f:
                            f.write(",".join([str(time()), user, str(station), queue, "1"]) + "\n")
                        releaseLock(lock)
                    else:
                        cur.execute("UPDATE %s SET visible = 0 WHERE station = (?)" % queue, (station,))
                        lock = acquireLock(private + room + ".log")
                        with open(private + room + ".log", "a+") as f:
                            f.write(",".join([str(time()), user, str(station), queue, "0"]) + "\n")
                        releaseLock(lock)
            except sqlite3.IntegrityError: 
                req.log_error("IntegrityError: Error updating station %d for user %s in queue %s from %s\r\n" % (station, user, queue, ip))
                conn.close()
                return apache.HTTP_INTERNAL_SERVER_ERROR
        conn.close()
        return apache.OK
    # 
    # If the page has just loaded and needs queue data stat
    # 
    elif 'firsttime' in query:
        curtime = time()*1000
        # long line that checks if a station number is in any of the queues
        station_in_queues = reduce(lambda a, b: a + b, [list(cur.execute("SELECT station FROM %s WHERE station = (?)" % q, (station,))) for q in queues])
        if len(station_in_queues) == 0:
            for q in queues:
                cur.execute("INSERT INTO %s VALUES (?, ?, ?)" % q, (station, 0, curtime))
                conn.commit()
        # non-destructive add, let user remain in place
        if not (anystudent or section == 'Outside Lab Hours' or (userinsection(user, section) and timeinsection(curtime, section)) or is_staff):
            # attempt to add station to queue but user was 
            # not in section, or section not in progress
            conn.close()
            req.content_type = "application/json"
            req.send_http_header()
            req.write('{"status": "failure", "reason": "You may not access the queue unless your section is in progress or you are in office hours."}')
            return apache.OK
        conn.close()
        req.content_type = "application/json"
        req.send_http_header()
        req.write(json.dumps(queues))
        return apache.OK
    #
    # Otherwise it is waiting for updates
    #
    elif 'sseupdate' in query:
        with conn:
            # clear users from station if they are not the current user OR were at the station more than three hours ago
            users_at_station = list(cur.execute("SELECT login FROM _user WHERE station = (?)", (station,)))
            if len(users_at_station) > 0 and user not in users_at_station:
                cur.execute("DELETE FROM _user where station = (?) and (login != (?) or time < (?))", (station, user, time()*1000 - (3*60*60)))
            # then we can safely add the current user to the _user table
            cur.execute("INSERT INTO _user (login, station, time) VALUES (?, ?, ?)", (user, station, time()*1000))
            id = [x for x in cur.execute("SELECT last_insert_rowid()")][0]
        req.headers_out['Cache-Control'] = 'no-cache;public'
        req.content_type = "text/event-stream;charset=UTF-8"
        req.send_http_header()
        req.write("\n\r")
        global wm
        wm = pyinotify.WatchManager()
        notifier = pyinotify.Notifier(wm, EventHandler(), timeout=30*1000)
        wdd = wm.add_watch(queue_db, pyinotify.IN_MODIFY, rec=True)
        # start pyinotify
        while True:
            notifier.process_events()
            while notifier.check_events():
                # above line returns after 30 seconds or if queue is updated
                notifier.read_events()
                notifier.process_events()
            try:
                req.write("data: %s\n\r" % json.dumps(getqueues()))
            except:
                wm.close()
                with conn:
                    cur.execute("DELETE FROM _user WHERE id = (?)", id)
                conn.close()
                try:
                    sys.exit(0)
                except:
                    os._exit(0)
        return apache.OK
    else:
        conn.close()
        req.content_type = "text/plain"
        req.send_http_header()
        req.write("Invalid request.")
        return apache.OK
