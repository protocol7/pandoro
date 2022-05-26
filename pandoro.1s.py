#!/usr/bin/env python3

# <bitbar.title>Pandoro</bitbar.title>
# <bitbar.version>v1.0</bitbar.version>
# <bitbar.author>Niklas Gustavsson</bitbar.author>
# <bitbar.author.github>protocol7</bitbar.author.github>
# <bitbar.desc>The love child of Trello and Pomodoro</bitbar.desc>

import json
import sys
import os.path
import time
from contextlib import contextmanager
from subprocess import Popen, PIPE

@contextmanager
def atomic_write(filepath, binary=False, fsync=False):
    """ Writeable file object that atomically updates a file (using a temporary file).

    :param filepath: the file path to be opened
    :param binary: whether to open the file in a binary mode instead of textual
    :param fsync: whether to force write the file to disk
    """

    tmppath = filepath + '~'
    while os.path.isfile(tmppath):
        tmppath += '~'
    try:
        with open(tmppath, 'wb' if binary else 'w') as file:
            yield file
            if fsync:
                file.flush()
                os.fsync(file.fileno())
        os.rename(tmppath, filepath)
    finally:
        try:
            os.remove(tmppath)
        except (IOError, OSError):
            pass


class Trello:
    @staticmethod
    def load_from_config(config):
        KEY, TOKEN, TODO_LIST_ID, DONE_LIST_ID = config["key"], config["token"], config["todo-list"], config["done-list"]

        return Trello(KEY, TOKEN, TODO_LIST_ID, DONE_LIST_ID)


    def __init__(self, key, token, todo_list_id, done_list_id):
        self.key = key
        self.token = token
        self.todo_list_id = todo_list_id
        self.done_list_id = done_list_id


    def fetch_tasks(self):
        import requests
        r = requests.get(f"https://api.trello.com/1/lists/{self.todo_list_id}/cards?key={self.key}&token={self.token}")

        r.raise_for_status()

        return {c["id"]: c["name"] for c in r.json()}


    def complete_task(self, card_id):
        data = {"pos": "top"}
        data["idList"] = self.done_list_id
        import requests
        r = requests.put(f"https://api.trello.com/1/cards/{card_id}?key={self.key}&token={self.token}", data=data)

        r.raise_for_status()

    def new_task(self, name, due_date):
        # TODO implement due_date
        data = {
            "name": name,
            "pos": "top",
            "idList": self.todo_list_id,
        }
        import requests
        r = requests.post(f"https://api.trello.com/1/cards?key={self.key}&token={self.token}", data=data)

        r.raise_for_status()


class Google:
    # Set up:
    # Get OAuth credentials: https://developers.google.com/workspace/guides/create-credentials#oauth-client-id
    #   Application type = desktop
    # Download json file and rename it to credentials.json
    # Stick in "~/.config/pandoro directory and run this script to authenticate. You should now get a token.json file
    # Delete credentials.json

    @staticmethod
    def load_from_config(config):
        list_id = config["list-id"]

        return Google(list_id)


    def __init__(self, list_id):
        self.list_id = list_id

        creds = self.get_creds()
        from googleapiclient.discovery import build
        self.service = build('tasks', 'v1', credentials=creds)


    def get_creds(self):
        import os.path
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        SCOPES = ['https://www.googleapis.com/auth/tasks']
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        token_file = os.path.expanduser("~/.config/pandoro/token.json")
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                cred_file = os.path.expanduser("~/.config/pandoro/credentials.json")
                flow = InstalledAppFlow.from_client_secrets_file(cred_file, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.json", 'w') as token:
                token.write(creds.to_json())

        return creds


    def fetch_tasks(self):
        tasks = self.service.tasks().list(tasklist=self.list_id, maxResults=100).execute().get("items", [])
        tasks = sorted(tasks, key=lambda t: t["position"])

        return {c["id"]: c["title"] for c in tasks}


    def complete_task(self, card_id):
        self.service.tasks().patch(tasklist=self.list_id, task=card_id, body={"status": "completed"}).execute()

        self.service.tasks().clear(tasklist=self.list_id).execute()


    def new_task(self, name, due_date):
        if due_date:
            due_date = due_date.isoformat() + "T00:00:00.000Z"

        self.service.tasks().insert(tasklist=self.list_id, body={"title": name, "due": due_date}).execute()


PANDA = "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAACXBIWXMAAA7EAAAOxAGVKw4bAAAFXElEQVRIx8VVX0xTZxT/Hbi7N7VWEcpgaEuRP5Ua0GZTYJkYIwkwnsT6oHMLhj34IDFT1y5xmZmJ6WZilggvxpngGqKJITxtOBmJIc00WGACYVSIVDtJa+kfOrraa3vPXqShA5csy7Lfy/1O7jnn+77z+53vAP8xCABEUaTS0tJPcnJyPiai9fF4/Me5ubnPIpFIsKKiQqyurq7V6XTVGo3mTQBYWlp67vV6J8bHx++53W5548aNeVu3bv1KpVI1MvPS4uLit7Ozs9/IsswEAFVVVec3bdr0eV5eHgmCgGAwyFlZWSMHDhz4uba29qPCwsKcDRs2QJIkAOBEIkHRaJR9Pt/i8PDwd729ve8qivJOXl4ekskkB4NBikQi58fHx8/RunXr3jCbzaGioiJ1YWEhACA3NxdNTU0wm80QRfFvSyDLMsbGxnD79m2EQiEAgM/nw/z8/NLDhw/zBEEQNES0XqVSMRGRwWDAwYMHWa/XEwAwMxMRLSdctpe/kiShpqaGi4qKqLe3F3Nzc6xSqYiINIIgaIRoNBpKpVKPgsFgudFohMViwZYtW/4xmXq9HhaLBQ6HA48fP0YqlXoUiURCyz/3tbS0LLlcLuXfwuVyKS0tLUvFxcX7Mk7gcDj6ZFlmZmZFURR+hZXrlfbrfGRZVnp6evoykjc0NJS73e4UM/PU1BRbrVbFYrGwzWZjr9f72g28Xi/bbDa2WCyK1WrlqakpVhRFcbvdqebm5jIAEABg7969R/V6PQ0PD/PZs2fx8uVLAOBAIACPx4Pu7m5+JdE00YlEAmfOnGGfzwcACAQCPDo6igsXLqC6uprq6+s/7O/vPycAQF1dXbOiKLDb7ZRMJkFEfOLECQKArq4udjqd1NDQkKEip9PJfr+fOjo6QETc2dlJyWQSdrude3p6qKamphnAOaG0tFTIz8/fMTg4iHA4zABQXl6O1tZWBoCrV6/C4/EwM2fcwOPxQJIkbm1tBQD09/fzzMwMwuEwBgcHubi4eIfRaBQErVa7Wa1Wi5OTk2m9+/1+9vl8NDExgRcvXrAkSelWWKF/TiQSNDAwgKqqKvb7/UREYGaenJwkk8kkarXazYIkSRpBEBCPx9MnjEajOHLkSNrevn37Kt2bTCYAgN1uBzNjRS8iHo9DEASIoqgRksmkrCgKdDrdmg1UUlKCnTt34u7du5iZmcFyCevr62EwGODxeFbF6HQ6KIqCVCqVEMLh8G+xWCzV2NiYdevWLZZlOV0KlUoFq9UKZuahoSHcuHEDAHD48GHes2cPrFYrnzp1CvF4HMskiaKIxsZGjkajSjgcfkYAMDAwMLZ79+4dY2NjdO3aNQQCAd62bRu1tbXBYDDw8rN++fJlEBF3dHSQoigMgJ4+fYru7m6enp6m/Px8tLe3s9lsJpfL9cv+/fvNAgAMDQ3dLCsr22E0GnHx4sWM6wYCAdy5cwc+nw/3798HMyMajcJgMKCpqQkFBQWw2WwZMaFQCE6n82Z64JhMpg2dnZ3ukpKSgrV4SKVS+PT0adSqRGQT4d4fCXx96RKys7PX5M3j8fhPnjxpnJiYiKapb29vbzh27Nj3Wq1WBJAuy/I6/sSDt0aHATA/f7uGRL1hlQ8ALCwsyA6Ho+XKlSs/YYUDAOD48ePvHzp0qEer1W7MyspaFfwXO2MDRVFoYWEh0tfX90FXV9cPGTN5Jerq6ja3tbV9WVFRcVStVouSJGVofCWYGYlEArFYTJ6dne25fv36F06n89mqob8WzGZz7q5du1oqKyvfMxgMlWq1uoiINK8S/x6LxeafPHny6/T0tPPBgwffj4yMhPB/4E817SlIfvERtAAAAABJRU5ErkJggg=="
WORK_TIME = 25 * 60
BREAK_TIME = 5 * 60

with(open(os.path.expanduser("~/.pandororc"))) as f:
    config = json.load(f)

tm_type = config.get("type", "trello")
if tm_type == "trello":
    task_manager = Trello.load_from_config(config)
if tm_type == "google":
    task_manager = Google.load_from_config(config)

ME = sys.argv[0]
STATE_FILE = "/tmp/pandoro"


# state management

def load_state():
    if os.path.isfile(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    else:
        return {}


def save_state(state):
    with atomic_write(STATE_FILE) as f:
        json.dump(state, f)


def refresh_state(state):
    ns = {}
    if "current" in state:
        ns["current"] = state["current"]
    if "status" in state:
        ns["status"] = state["status"]
    if "time" in state:
        ns["time"] = state["time"]

    ns["tasks"] = task_manager.fetch_tasks()

    return ns


# util functions

def calc_remaining(state):
    status = state.get("status", None)
    if status is None:
        return None

    slot_time = WORK_TIME if status == "work" else BREAK_TIME

    end = state["time"] + slot_time
    remaining = end - epoch()

    return remaining


def format_time(t):
    return "%02d:%02d" % (t // 60, t % 60)


def epoch():
    return int(time.time())


def osascript(script):
    p = Popen(['osascript'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate(script)
    return stdout.strip().decode("utf-8")


def notify(msg):
    osascript(b"display notification \"" + msg.encode("UTF-8") + b"\" with title \"Pandoro\" sound name \"default\"")


# commands
def new_task(state):
    task = osascript(b"""set theString to text returned of (display dialog "New task" default answer "" buttons {"OK","Cancel"} default button 1)""")

    new_state = do_new_task(state, task)

    notify("New task added")

    return new_state

def do_new_task(state, task):
    if task:
        # detect due date
        import re
        import datetime

        due_date = None
        m = re.search(r" \d{4}-\d{2}-\d{2}$", task)
        if m:
            due_date = datetime.date.fromisoformat(m.group()[1:])
            task = task[0:m.start()]
        elif task.endswith(" tomorrow"):
            due_date = datetime.date.today() + datetime.timedelta(days=1)
            task = task[0:-9]

        task_manager.new_task(task, due_date)

    return refresh_state(state)


def complete_task(state, tid, next_id):
    task_manager.complete_task(tid)

    state["current"] = next_id

    return refresh_state(state)


def switch_task(state, tid):
    state["current"] = tid


def start_session(state, session_type):
    if state.get("status") != session_type:
        state["time"] = epoch()

    state["status"] = session_type


def pause(state):
    del state["status"]
    del state["time"]

def current_task(state):
    print(state.get("current", ""))

def alfred_list(state):
    # list tasks, excluding current, and outputs in Alfred JSON format
    # https://www.alfredapp.com/help/workflows/inputs/script-filter/json/
    current_id = state.get("current", None)

    items = []
    for tid, name in state["tasks"].items():
        if tid == current_id:
            continue

        items.append({
            "title": name,
            "arg": tid,
		    "icon": {
                "path": "/Users/ngn/src/pandoro/panda.png"
            }
        })

    print(json.dumps({"items": items}))

# tick
def tick(state):
    current_id = state.get("current", None)

    remaining = calc_remaining(state)
    status = state.get("status", None)

    if remaining is None:
        s = ""
    else:
        if remaining <= 0:
            if status == "work":
                state["status"] = "break"
                state["time"] = epoch()

                notify("Time for break")
            elif status == "break":
                state["status"] = "work"
                state["time"] = epoch()
                notify("Time for work")

            remaining = calc_remaining(state)

            save_state(state)

        if status == "work" or status == "break":
            s = " \033[32m" if status == "work" else " \033[33m"
            s += format_time(remaining)
            s += "\033[0m"

        # current task name
        if status == "work":
            s += " - "
            msg = state["tasks"].get(current_id, "")
            if len(msg) > 19:
                msg = msg[:20] + "…"
            msg = msg.ljust(20)
            s += msg

    s += "| trim=false image=" + PANDA

    print(s)
    print("---")
    if status == "work":
        if current_id:
            print("Complete and continue...")
            for tid, name in state["tasks"].items():
                if tid != current_id:
                    print("-- %s |bash=\"%s\" param1=done param2=%s param3=%s terminal=false length=50" % (name, ME, current_id, tid))

        print("Switch...")
        for tid, name in state["tasks"].items():
            if tid != current_id:
                print("-- %s |bash=\"%s\" param1=switch param2=%s terminal=false length=50" % (name, ME, tid))

    print("New task... |bash=\"%s\" param1=create terminal=false" % ME)
    if status != "work":
        print("Get to work |bash=\"%s\" param1=work terminal=false" % ME)
    if status != "break":
        print("Take a break |bash=\"%s\" param1=break terminal=false" % ME)
    print("---")
    if status:
        print("Pause |bash=\"%s\" param1=pause terminal=false" % ME)
    print("Refresh |bash=\"%s\" param1=refresh terminal=false" % ME)


if __name__ == "__main__":
    # read state from file
    state = load_state()

    # if no state present, refresh to get defaults
    if not state:
        state = refresh_state(state)

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "switch":
            switch_task(state, sys.argv[2])
        elif cmd == "done":
            if len(sys.argv) > 3:
                tid = sys.argv[2]
                next_id = sys.argv[3]
            else:
                tid = state.get("current", None)
                next_id = sys.argv[2]

            if tid:
                state = complete_task(state, tid, next_id)
        elif cmd == "work" or cmd == "break":
            start_session(state, cmd)
        elif cmd == "pause":
            pause(state)
        elif cmd == "refresh":
            state = refresh_state(state)
        elif cmd == "create":
            if len(sys.argv) > 2:
                state = do_new_task(state, sys.argv[2])
            else:
                state = new_task(state)
        elif cmd == "alfred-list":
            alfred_list(state)
        elif cmd == "current":
            current_task(state)

        save_state(state)
    else:
        tick(state)