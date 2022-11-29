#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os, io, sys, codecs, re
from datetime import datetime, timedelta
from urllib.parse import parse_qs
from json import load

username = os.environ['REMOTE_USER']
ip = os.environ['REMOTE_ADDR']
private = os.environ['DOCUMENT_ROOT'] + os.environ["CONTEXT_PREFIX"] + '/private/labutils/'

# init all variables
def doexec(path):
    exec(compile(open(path).read(), path, "exec"), globals())

try:
    doexec(private + "config.py")
except Exception as e:
    print("Content-Type: text/plain\r\n")
    print("Error in config: " + str(e))
    exit(0)

# enables unicode printing
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# get IP and TA lists
try:
    station = getstation(os.environ["REMOTE_ADDR"])
except: 
    # exception indicates IP does not belong in list
    print ("Content-Type: text/html\r\n")
    print ("<h2>Access denied</h2>")
    exit(0)

# check that we are being opened during a lab section
section = getactivesection()

# check if user is staff
is_staff = username in staff

# if section was never set, it means no section is currently running
if section is None:
    section = "Outside Lab Hours"

# load the HTML with section data
print ("Content-Type: text/html\r\n")
with io.open('index.html', 'r', encoding='utf8') as file:
    # fill section information here
    data = file.read().replace("Section Information Here", section)
    # fill username
    data = data.replace("--userstation--", str(station))
    data = data.replace("--is-staff--", "true" if is_staff else "false")
    # send HTML
    print(data)
