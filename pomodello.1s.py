#!/usr/local/bin/python3

import json
import requests
import sys
import tempfile
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


PANDA = "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAACXBIWXMAAA7EAAAOxAGVKw4bAAAFXElEQVRIx8VVX0xTZxT/Hbi7N7VWEcpgaEuRP5Ua0GZTYJkYIwkwnsT6oHMLhj34IDFT1y5xmZmJ6WZilggvxpngGqKJITxtOBmJIc00WGACYVSIVDtJa+kfOrraa3vPXqShA5csy7Lfy/1O7jnn+77z+53vAP8xCABEUaTS0tJPcnJyPiai9fF4/Me5ubnPIpFIsKKiQqyurq7V6XTVGo3mTQBYWlp67vV6J8bHx++53W5548aNeVu3bv1KpVI1MvPS4uLit7Ozs9/IsswEAFVVVec3bdr0eV5eHgmCgGAwyFlZWSMHDhz4uba29qPCwsKcDRs2QJIkAOBEIkHRaJR9Pt/i8PDwd729ve8qivJOXl4ekskkB4NBikQi58fHx8/RunXr3jCbzaGioiJ1YWEhACA3NxdNTU0wm80QRfFvSyDLMsbGxnD79m2EQiEAgM/nw/z8/NLDhw/zBEEQNES0XqVSMRGRwWDAwYMHWa/XEwAwMxMRLSdctpe/kiShpqaGi4qKqLe3F3Nzc6xSqYiINIIgaIRoNBpKpVKPgsFgudFohMViwZYtW/4xmXq9HhaLBQ6HA48fP0YqlXoUiURCyz/3tbS0LLlcLuXfwuVyKS0tLUvFxcX7Mk7gcDj6ZFlmZmZFURR+hZXrlfbrfGRZVnp6evoykjc0NJS73e4UM/PU1BRbrVbFYrGwzWZjr9f72g28Xi/bbDa2WCyK1WrlqakpVhRFcbvdqebm5jIAEABg7969R/V6PQ0PD/PZs2fx8uVLAOBAIACPx4Pu7m5+JdE00YlEAmfOnGGfzwcACAQCPDo6igsXLqC6uprq6+s/7O/vPycAQF1dXbOiKLDb7ZRMJkFEfOLECQKArq4udjqd1NDQkKEip9PJfr+fOjo6QETc2dlJyWQSdrude3p6qKamphnAOaG0tFTIz8/fMTg4iHA4zABQXl6O1tZWBoCrV6/C4/EwM2fcwOPxQJIkbm1tBQD09/fzzMwMwuEwBgcHubi4eIfRaBQErVa7Wa1Wi5OTk2m9+/1+9vl8NDExgRcvXrAkSelWWKF/TiQSNDAwgKqqKvb7/UREYGaenJwkk8kkarXazYIkSRpBEBCPx9MnjEajOHLkSNrevn37Kt2bTCYAgN1uBzNjRS8iHo9DEASIoqgRksmkrCgKdDrdmg1UUlKCnTt34u7du5iZmcFyCevr62EwGODxeFbF6HQ6KIqCVCqVEMLh8G+xWCzV2NiYdevWLZZlOV0KlUoFq9UKZuahoSHcuHEDAHD48GHes2cPrFYrnzp1CvF4HMskiaKIxsZGjkajSjgcfkYAMDAwMLZ79+4dY2NjdO3aNQQCAd62bRu1tbXBYDDw8rN++fJlEBF3dHSQoigMgJ4+fYru7m6enp6m/Px8tLe3s9lsJpfL9cv+/fvNAgAMDQ3dLCsr22E0GnHx4sWM6wYCAdy5cwc+nw/3798HMyMajcJgMKCpqQkFBQWw2WwZMaFQCE6n82Z64JhMpg2dnZ3ukpKSgrV4SKVS+PT0adSqRGQT4d4fCXx96RKys7PX5M3j8fhPnjxpnJiYiKapb29vbzh27Nj3Wq1WBJAuy/I6/sSDt0aHATA/f7uGRL1hlQ8ALCwsyA6Ho+XKlSs/YYUDAOD48ePvHzp0qEer1W7MyspaFfwXO2MDRVFoYWEh0tfX90FXV9cPGTN5Jerq6ja3tbV9WVFRcVStVouSJGVofCWYGYlEArFYTJ6dne25fv36F06n89mqob8WzGZz7q5du1oqKyvfMxgMlWq1uoiINK8S/x6LxeafPHny6/T0tPPBgwffj4yMhPB/4E817SlIfvERtAAAAABJRU5ErkJggg=="
WORK_TIME = 25 * 60
BREAK_TIME = 5 * 60

me = sys.argv[0]
state_file = "/tmp/pomodello"


def load_config():
    with(open(os.path.expanduser("~/.pomodellorc"))) as f:
        j = json.load(f)

        return j["key"], j["token"], j["todo-list"], j["done-list"]

key, token, list_id, done_list_id = load_config()


def load_state():
    if os.path.isfile(state_file):
        with open(state_file) as f:
            return json.load(f)

    else:
        return {}


def save_state(state):
    with atomic_write(state_file) as f:
        json.dump(state, f)


def fetch_tasks():
    r = requests.get(f"https://api.trello.com/1/lists/{list_id}/cards?key={key}&token={token}")

    r.raise_for_status()

    return {c["id"]: c["name"] for c in r.json()}

def move_task(card_id, list_id):
    data = {"idList": list_id, "pos": "top"}
    r = requests.put(f"https://api.trello.com/1/cards/{card_id}?key={key}&token={token}", data=data)

    r.raise_for_status()


def new_task():
    scpt = b"""set theString to text returned of (display dialog "New task" default answer "" buttons {"OK","Cancel"} default button 1)"""

    p = Popen(['osascript'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate(scpt)
    name = stdout.strip().decode("utf-8")

    if name:
        data = {
            "name": name,
            "pos": "top",
            "idList": list_id,
        }
        r = requests.post(f"https://api.trello.com/1/cards?key={key}&token={token}", data=data)

        r.raise_for_status()


def refresh_state(state):
    ns = {}
    if "current" in state:
        ns["current"] = state["current"]
    if "status" in state:
        ns["status"] = state["status"]
    if "time" in state:
        ns["time"] = state["time"]

    ns["tasks"] = fetch_tasks()

    return ns


def tick(state):
    status = state.get("status", None)
    if status is None:
        return None

    slot_time = WORK_TIME if status == "work" else BREAK_TIME

    end = state["time"] + slot_time
    remaining = end - epoch()

    return remaining


def format_time(t):
    min = t // 60
    sec = t % 60
    return "%02d:%02d" % (min, sec)

def epoch():
    return int(time.time())

state = load_state()

if state == {}:
    state = refresh_state(state)

current_id = state.get("current", None)

if len(sys.argv) > 1:
    cmd = sys.argv[1]

    if cmd == "switch":
        state["current"] = sys.argv[2]
    elif cmd == "complete":
        tid = sys.argv[2]
        next_id = sys.argv[3]
        move_task(tid, done_list_id)

        state["current"] = next_id

        state = refresh_state(state)
    elif cmd == "work" or cmd == "break":
        if state.get("status") != cmd:
            state["time"] = epoch()

        state["status"] = cmd
    elif cmd == "pause":
        del state["status"]
        del state["time"]
    elif cmd == "refresh":
        state = refresh_state(state)
    elif cmd == "create":
        new_task()

        state = refresh_state(state)

    save_state(state)
else:
    remaining = tick(state)
    status = state.get("status", None)

    if remaining is None:
        s = ""
    else:
        if remaining <= 0:
            reset = False
            if status == "work":
                status = "break"
                reset = True
            elif status == "break":
                status = "work"
                reset = True

            if reset:
                state["status"] = status
                state["time"] = epoch()

            remaining = tick(state)

            save_state(state)

        if status == "work" or status == "break":
            s = " \033[1;30m"
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
    if current_id:
        print("Complete and continue...")

        for tid, name in state["tasks"].items():
            if tid != current_id:
                print("-- %s |bash=\"%s\" param1=complete param2=%s param3=%s terminal=false length=50" % (name, me, current_id, tid))


    print("Switch...")
    for tid, name in state["tasks"].items():
        if tid != current_id:
            print("-- %s |bash=\"%s\" param1=switch param2=%s terminal=false length=50" % (name, me, tid))

    print("New task... |bash=\"%s\" param1=create terminal=false" % me)
    if status != "work":
        print("Work |bash=\"%s\" param1=work terminal=false" % me)
    if status != "break":
        print("Break |bash=\"%s\" param1=break terminal=false" % me)
    if status:
        print("Pause |bash=\"%s\" param1=pause terminal=false" % me)
    print("Refresh |bash=\"%s\" param1=refresh terminal=false" % me)