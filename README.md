# labutils
Lab Queue System

## Objective
labutils was designed to provide a straightforward way of adding students in a lab room at designated lab stations to a queue.  This application is intended for ECE classes at Purdue University.

The system also features a simple timer for any in-lab exams, quizzes, or other such timed assignments.

![image width="200"](https://user-images.githubusercontent.com/12859429/187915228-e7293cee-e781-4daa-bef5-329fd80d8b33.png)
![image width="200"](https://user-images.githubusercontent.com/12859429/187916324-f3af417c-5229-4054-b9df-aea4a463a116.png)
![image width="200"](https://user-images.githubusercontent.com/12859429/187916118-ec1c87a7-f1d1-4b9e-9362-8b32e2e0d661.png)
![image width="200"](https://user-images.githubusercontent.com/12859429/187915856-01fb97e5-23c1-468c-aadb-add5e097c41b.png)

## Installation
The software assumes you are running an Apache container for your course on templeton.ecn, with split public_html and private directories, and with mod_python enabled for Server-Sent-Event (SSE) handling.  (Ideally, any setup with Apache could work.)  

This repository is split into web (which goes into the public_html folder) and private (which goes into the private folder) branches.  We suggest private/labutils and web/labutils as the directories you should clone into, ensuring that you switch to the right branch for each folder.  

To ensure that only persons associated with Purdue University can access this page (this is also crucial to how the queue works), add an .htaccess file to the web directory with the lines (as per [Purdue I2A2 Auth security measures](https://engineering.purdue.edu/ECN/Support/KB/Docs/WebServerAuthenticat)):

```
# if you don't mind using Basic Auth for simple career account username/password entry
require any-user
```

or


```
# if you would like to use BoilerKey
AuthType CAS
Require valid-user
```

In the admin directory that falls under web, add restrictions to ensure no one other than yourself can see the page.  "require i2a2-user adminuser" or "Require user adminuser" should work (depending on which of the two you used above).

Once cloned, you need to configure the queue software to recognize the lab machines students will access the queue from.  This is a restriction to ensure that only students in lab can add themselves to the queue.  Configuration is specified as a JSON file with the following format:

```
{
    "room": "roomname", 
    "courseid": "ecexxxxx", 
    "ip_to_station": {
        "1.2.3.4": "1", 
        # ...
    }, 
    "disabled": false, 
    "coursename": "ECE XXXXX", 
    "anystudent": false, 
    "sections": [
        "Section X,Sunday,12:00AM-11:59PM",
        # ...
    ]
}
```

In which you will fill out each field with the details of your course, and then save to roomname.json in the private/labutils directory.  

By default, the queue system has a checkoff and help queue, but you can configure as many queues with whatever names you like.  The script "db_init.py" configures a SQLite file database that stores the entries for each queue.  You can modify this to set up a database with your own queues.  Then, create an empty file named "roomname.db", and run "python3 db_init.py roomname.db" to set up the database with the queues and user information (stored when a user joins/leaves a queue).

Once set up, navigate to the labutils page from one of the lab machines that you will use for your course.  Try joining/leaving all the queues to ensure it works.  

Next, add "/admin" at the end of the labutils URL.  (Ensure that only you are able to access it!)  You should see the log with you adding/removing yourself from the queues.  Test the Download and "Backup and Clear" log buttons on the page to see that they are working as well.

Maintenence: 

Not much maintenence is required except occassionally clearing the log at the end of each week to ensure the log files do not get big via the admin page.  By the time you make 20 backups, the oldest backup is then deleted to make space for the newest one.  
