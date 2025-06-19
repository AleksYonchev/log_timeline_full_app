import requests
import win32evtlog
import win32evtlogutil

def get_latlon():
    response = requests.get("https://ipinfo.io/json")
    if response.status_code == 200:
        data = response.json()
        coords = data.get("loc").split(',')
        location = {
            "lat": coords[0],
            "lon": coords[1],
        }
        return location
    else:
        return {"error": "Unable to fetch geolocation data"}

with open('eventlog.log', 'w') as file:
    pass

server = 'localhost'
localhost_latlon = get_latlon()
logtype = 'Application' # 'Application' # 'Security' # 'Windows PowerShell'
hand = win32evtlog.OpenEventLog(server,logtype)
totalEventsCount = win32evtlog.GetNumberOfEventLogRecords(hand)
print(f"Total events: {totalEventsCount}\n")
flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

i = 0
from_i = 0
to_i = 6
while True:
    events = win32evtlog.ReadEventLog(hand, flags, 0)
    if events:
        for event in events:
            i = i + 1
            if i < from_i:
                continue
            if i > to_i:
                break
            try:
                message = win32evtlogutil.SafeFormatMessage(event, logtype)
            except Exception as msg_err:
                message = f"Could not retrieve message: {msg_err}"
            message = ' '.join(message.splitlines())
            msg = f'{event.TimeGenerated} | {message} | lat:{localhost_latlon['lat']} | lon:{localhost_latlon['lon']}\n'
            with open("eventlog.log", "a") as myfile:
                myfile.write(msg)
    else:
        break