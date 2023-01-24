# install libs
import subprocess
import enum
import sys
if sys.platform == "win32":
    try:
        startupinfo = subprocess.STARTUPINFO
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    except:
        startupinfo = None
else:
    startupinfo = None
subprocess.check_output(["pip3", "install", "cryptography", "colorama", "toml", "pyngrok"], shell=False).decode()

# import required libraries
from colorama import Fore as Colour
import cryptography.fernet as fernet
import pyngrok.ngrok as ngrok
import socket
import toml
import os

### LOGGING ###

class Mode(enum.Enum):
    Fatal = 0
    Error = 1
    Warn = 2
    Success = 3
    Wrap = 4

def log(text: str, mode: Mode | None = Mode.Success, **kwargs) -> None:
    wrap = lambda t, c : c + t + Colour.RESET
    if mode == Mode.Fatal:
        print(wrap(text, Colour.LIGHTRED_EX))
        exit(1)
    elif mode == Mode.Error:
        print(wrap(text, Colour.LIGHTRED_EX))
    elif mode == Mode.Warn:
        print(wrap(text, Colour.LIGHTYELLOW_EX))
    elif mode == Mode.Success:
        print(wrap(text, Colour.LIGHTGREEN_EX))
    elif mode == Mode.Wrap:
        print(wrap(text, kwargs.get("colour", Colour.LIGHTWHITE_EX)))
    else:
        print(text)

def fancy(text: str, colour: str | None) -> str:
    return input((colour if colour != None else Colour.LIGHTWHITE_EX) + text + Colour.RESET)

### CONFIG ###

CONFIG_PATH = "config.toml"
# custom config
args = sys.argv[1:]
if len(args) > 0:
    CONFIG_PATH = args[0]

# load config
if not os.path.isfile(CONFIG_PATH):
    log(f"configuration file '{CONFIG_PATH}' does not exist.", Mode.Fatal)
else:
    log(f"loaded config '{CONFIG_PATH}'.\n", Mode.Success)
with open(CONFIG_PATH, "r") as f:
    raw = toml.load(f)
    try:
        KEY = raw["encryption"]["key"]
        NGROK = raw["server"]["ngrok"]
        HOST = raw["server"]["host"]
        PORT = raw["server"]["port"]
        EXIT = raw["global"]["exit_command"]
        BUFFER = raw["global"]["buffer"]
    except:
        log("failed to load 'config.toml' due to invalid formatting.", Mode.Fatal)

### ENCRYPTION ###

try:
    crypter = fernet.Fernet(KEY.encode())
except ValueError:
    log("invalid key.", Mode.Fatal)

### SOCKET LOGIC ###

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# server or client?
choice = ""
while choice == "":
    log("what do you wish to do?", Mode.Wrap, colour=Colour.LIGHTMAGENTA_EX)
    log(" 1. connect to a chat.", Mode.Wrap, colour=Colour.LIGHTWHITE_EX)
    log(" 2. host the chat.", Mode.Wrap, colour=Colour.LIGHTWHITE_EX)
    choice = fancy("> ", Colour.LIGHTBLACK_EX)
    try:
        choice = int(choice)
    except:
        continue
    choice = "c" if choice == 1 else "h" if choice == 2 else ""

# client
if choice == "c":
    try:
        HOST, PORT = fancy("host: ", Colour.LIGHTCYAN_EX), int(fancy("port: ", Colour.LIGHTCYAN_EX))
    except ValueError:
        log("failed to parse host/port. ensure that the port is an integer.", Mode.Fatal)
    sock.connect((HOST, PORT))
    log(f"\nconnected to '{HOST}'.", Mode.Wrap, colour=Colour.GREEN)
    log(f"type '{EXIT}' to quit.\n", Mode.Wrap, colour=Colour.YELLOW)
    # now create message loop
    while True:
        data = fancy("[you]> ", Colour.LIGHTGREEN_EX)
        if len(data) < 1:
            continue
        else:
            sock.send(crypter.encrypt(data.encode()))
            if data == EXIT:
                break
        # await incoming message!
        d = sock.recv(BUFFER)
        if not d:
            break
        cr = crypter.decrypt(d).decode()
        if cr == EXIT:
            break
        log(f"\n[{HOST}]> {cr}\n", Mode.Warn)
# server
elif choice == "h":
    if NGROK:
        try:
            tunnel = ngrok.connect(PORT, "tcp").public_url
        except:
            log("\nfailed to create ngrok tunnel.", Mode.Fatal)
        log(f"\nngrok tunnel '{tunnel}' created.", Mode.Success)

    # initiate
    sock.bind((HOST, PORT))
    sock.listen(1)
    # wait for client
    conn, addr = sock.accept()
    log(f"\nclient of IP '{addr[0]}' has connected.", Mode.Wrap, colour=Colour.LIGHTCYAN_EX)
    log(f"type '{EXIT}' to quit.", Mode.Wrap, colour=Colour.YELLOW)
    while True:
        d = conn.recv(BUFFER)
        if not d:
            break
        cr = crypter.decrypt(d).decode()
        if cr == EXIT:
            break
        log(f"\n[{addr[0]}]> {cr}\n", Mode.Warn)
        data = fancy("[you]> ", Colour.LIGHTGREEN_EX)
        if len(data) < 1:
            continue
        else:
            conn.send(crypter.encrypt(data.encode()))
            if data == EXIT:
                break

# log disconnection
log(f"\nconnection terminated.", Mode.Error)
