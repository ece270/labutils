"""
The JSON config files in this directory will 
provide class info, including names, room, 
IP-to-station mappings, and section information.

This script will first determine which config 
to pull based on who is asking.  The global 
variable IP will be defined by the calling 
script, which will determine which room to use 
(since the IP should belong to a lab machine, 
which should be specified in the JSON file for 
its room) and which queue to display as a result.
The rest of the information in the config is 
passed to the calling script as well as different 
variables (room disabled boolean, any student can 
join boolean, ip-to-station mapping, etc.)
"""

if "ip" not in locals():
    raise Exception("No IP was passed.  You may be running this script wrong.")

try:
    private = os.environ['DOCUMENT_ROOT'] + os.environ['CONTEXT_PREFIX'] + '/private/labutils/'
except KeyError:
    # os.environ['DOCUMENT_ROOT'] is not set by CGI resulting in a exception
    # so we are being invoked by mod_python, so we need different env vars
    private = os.environ['HOME'] + '/private/labutils/'

configs = [x for x in os.listdir(private) if x.endswith("json")]
raw_configs = []
config_json = None
for c in configs:
    try:
        data = load(open(private + c))
    except:
        raise Exception("Error parsing JSON file.  Check for syntax errors or extraneous commas.")
    raw_configs.append(data)
    if ip in data["ip_to_station"]:
        config_json = data

if config_json is None:
    raise Exception("Your IP is not permitted to access the lab queue.")

sections = config_json["sections"]
ip_to_station = config_json["ip_to_station"]
room = config_json["room"]
coursename = config_json["coursename"]
anystudent = config_json["anystudent"]
roomdisabled = config_json["disabled"]

queue_db = private + room + '.db'

if roomdisabled:
    raise Exception("The queue has been disabled for this room.  Send an email to course staff if this is an error.")

def getstation(ip):
    global station
    if ip not in ip_to_station:
        raise Exception("IP is invalid")
    station = ip_to_station[ip]
    return station

def getstaff():
    global staff, section_student
    staff = section_student[0]

def getstudentsections():
    global section_student
    with open(private + 'users.conf') as f:
        data = [x for x in f.read().split("\n") if x != '']
        section_student = {}
        for l in data:
            split = l.split(",")
            if len(split) != 2: continue
            # "0" -> 0, "023" -> 23, "017" -> 17...
            section = 0 if split[1] == "0" else int(split[1])
            if section not in section_student:
                section_student[section] = [split[0]]
            else:
                section_student[section].append(split[0])

def isofficehoursweek():
    week = datetime.now().isocalendar()[1]
    virtual_lab_weeks = [
	11  # spring break
    ]
    return week in virtual_lab_weeks

def getactivesection():
    global sections
    if sections is None:
        raise Exception("JSON file not loaded.")
    now = datetime.now()
    section = None
    # sectionnum,day,time
    for s,d,t in [x.split(",") for x in sections]:
        # skip days that are not today
        if d != now.strftime("%A"):
            continue
        # check if we are in region of day
        t = t.split("-")
        sectionS = datetime.strptime("%s-%s-%s %s %s" % (now.strftime("%Y"), now.strftime("%m"), now.strftime("%d"), d, t[0]), "%Y-%m-%d %A %I:%M%p") - timedelta(minutes=5)
        sectionE = datetime.strptime("%s-%s-%s %s %s" % (now.strftime("%Y"), now.strftime("%m"), now.strftime("%d"), d, t[1]), "%Y-%m-%d %A %I:%M%p") + timedelta(minutes=5)
        if sectionS < now and now < sectionE:
            section = "%s - %s %s to %s" % (s, d, t[0], t[1])
    if section is None:
        section = 'Outside Lab Hours'
    return section

# Call functions to set up globals
getstudentsections()
getstaff()
getactivesection()
