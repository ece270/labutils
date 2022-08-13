#! /usr/bin/env python3
import os, sys
from mod_python import apache, util
from json import load, dump, dumps
from time import time, sleep
import pyinotify

try:
    private = os.environ['DOCUMENT_ROOT'] + os.environ['CONTEXT_PREFIX'] + '/private/labutils/'
except KeyError:
    # os.environ['DOCUMENT_ROOT'] is not set by CGI resulting in a exception
    # so we are being invoked by mod_python, so we need different env vars
    private = os.environ['HOME'] + '/private/labutils/'

def getdblog(room):
    with open(private + room + ".log") as f:
        data = [x.replace('\n', '').split(",") for x in f.readlines()]
    return data

def handler(req):
    # initialize some variables
    user = req.user
    query = util.FieldStorage(req)
    ip = req.useragent_ip

    class EventHandler(pyinotify.ProcessEvent):
        def process_IN_MODIFY(self, event):
            try:
                data = json.dumps(getdblog(room))
                sys.stderr.write("writes out - " + data + "\r\n")
                sys.stderr.flush()
                req.write("data: %s\n\r" % data)
            except:
                pass

    # now check our variables
    accepted_keys = ['sseupdate', 'roomdisabled', 'anystudent', 'clearlog', 'log']
    querychecked = any([x in query for x in accepted_keys]) and 'room' in query
    
    # this section handles disabling a room
    if querychecked and 'roomdisabled' in query:
        room = query.get("room", None)
        disabled = True if query.get("roomdisabled", None) == "true" else False
        if os.path.exists(private + "/" + room + ".json"):
            with open(private + "/" + room + ".json") as f:
                json = load(f)
            json["disabled"] = disabled
            with open(private + "/" + room + ".json", "w+") as f:
                dump(json, f, indent=4)
            req.content_type = "text/plain"
            req.send_http_header()
            req.write("success")
            return apache.OK
        else:
            req.content_type = "text/plain"
            req.send_http_header()
            req.write("invalid room")
            return apache.OK
    # this section handles enabling any student to join a room
    elif querychecked and 'anystudent' in query:
        room = query.get("room", None)
        anystudent = True if query.get("anystudent", None) == "true" else False
        if os.path.exists(private + "/" + room + ".json"):
            with open(private + "/" + room + ".json") as f:
                json = load(f)
            json["anystudent"] = anystudent
            with open(private + "/" + room + ".json", "w+") as f:
                dump(json, f, indent=4)
            req.content_type = "text/plain"
            req.send_http_header()
            req.write("success")
            return apache.OK
        else:
            req.content_type = "text/plain"
            req.send_http_header()
            req.write("invalid room")
            return apache.OK
    elif querychecked and 'log' in query:
        room = query.get("room", None)
        if not os.path.exists(private + room + ".log"):
            with open(private + room + ".log", "w+") as f:
                data = f.write("")
        req.content_type = "application/json"
        req.send_http_header()
        req.write(dumps(getdblog(room)))
        return apache.OK
    elif querychecked and 'clearlog' in query:
        room = query.get("room", None)
        req.content_type = "text/plain"
        req.send_http_header()
        # should be a real room
        if os.path.exists(private + room + ".db"):
            with open(private + room + ".log", "w+") as f:
                data = f.write("")
            req.write("cleared")
            return apache.OK
        else:
            req.write("invalid")
            return apache.OK
    elif querychecked and 'sseupdate' in query:
        room = query.get("room", None)
        if not os.path.exists(private + room + ".log"):
            with open(private + room + ".log", "w+") as f:
                f.write("")
        req.headers_out['Cache-Control'] = 'no-cache;public'
        req.content_type = "text/event-stream;charset=UTF-8"
        req.send_http_header()
        req.write("\n\r")
        global wm
        wm = pyinotify.WatchManager()
        notifier = pyinotify.Notifier(wm, EventHandler(), timeout=30*1000)
        wdd = wm.add_watch(private + room + '.log', pyinotify.IN_MODIFY, rec=True)
        # start pyinotify
        while True:
            notifier.process_events()
            while notifier.check_events():
                # above line returns after 30 seconds or if queue is updated
                notifier.read_events()
                notifier.process_events()
            try:
                req.write("data: %s\n\r" % dumps(getdblog(room)))
            except:
                wm.close()
                try:
                    sys.exit(0)
                except:
                    os._exit(0)
        return apache.OK
    # invalid request
    else:
        req.content_type = "text/plain"
        req.send_http_header()
        req.write("invalid")
        return apache.OK
