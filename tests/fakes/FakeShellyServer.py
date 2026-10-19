"""A Shelly Gen2 plug on localhost for the lamp tests (SPEC_lamp_switch.md §11, D13) — no hardware in the suite.

Speaks the subset the app uses: GET /shelly (never authenticated), /rpc/Shelly.GetDeviceInfo,
/rpc/Switch.Set (on, toggle_after), /rpc/Switch.GetStatus; and over POST /rpc the plug memory (KVS.*, Script.*,
Sys.GetStatus) plus the factory-tool calls (Switch.SetConfig/GetConfig, Shelly.SetAuth). With a password it challenges exactly like the real
plug — Digest with `algorithm=SHA-256` (§14 R1) — so a client that only speaks MD5 fails here too.
The timer semantics are the ones measured on the real plug (§15.3): an on WITH toggle_after (re)starts the
timer, an on WITHOUT it cancels it, off clears it. Time is an injectable clock so tests never sleep for a cap.
"""
import hashlib
import json
import re
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeShellyServer:

    REALM = "shellyplusplugs-e86beae3cb60"
    MAC = "E86BEAE3CB60"

    def __init__(self, password=None, apower=11.2, clock=time.monotonic, mac=MAC, gen=2):
        self.password = password
        self.lampWatts = apower
        self.clock = clock
        self.mac = mac
        self.gen = gen
        self.output = False
        self.timerStartedAt = None
        self.timerDuration = None
        self.dark = False                       # True: drop every connection (plug unreachable)
        self.uiConfig = None                    # the last PLUGS_UI.SetConfig config (LED ring)
        self.silent = False                     # True: accept, never answer (plug gone: the client times out)
        self.calls = []                         # [(method, params)] of every authenticated /rpc call
        # Plug memory (SPEC_shelly_instrument_memory.md §4.7), with the limits measured on the real plug (§7.2/§7.3).
        self.kvs = {}
        self.scripts = {}                       # id -> {"name", "code"}
        self.nextScriptId = 1
        self.fsFree = 126976
        self.switchConfig = {"initial_state": "on", "auto_off": False, "auto_off_delay": 60.0}
        self.authHa1 = None                     # set by Shelly.SetAuth
        self.lock = threading.Lock()
        self.__nonce = "%x" % int(time.time())
        server = self
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), self.__handlerClass(server))
        self.httpd.daemon_threads = True
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    # --- lifecycle ---------------------------------------------------------------------------------------
    @property
    def host(self):
        return "127.0.0.1:%d" % self.httpd.server_address[1]

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()

    # --- state -------------------------------------------------------------------------------------------
    def tick(self):
        """Apply an expired toggle_after (called on every request and by tests)."""
        with self.lock:
            if self.timerDuration is not None and self.clock() - self.timerStartedAt >= self.timerDuration:
                self.output = not self.output
                self.timerStartedAt = self.timerDuration = None

    def callsTo(self, method):
        return [params for name, params in self.calls if name == method]

    def offCalls(self):
        return [params for params in self.callsTo("Switch.Set") if params.get("on") == "false"]

    def __rpc(self, method, params):
        self.tick()
        with self.lock:
            self.calls.append((method, params))
            if method == "Shelly.GetDeviceInfo":
                return 200, self.__deviceInfo()
            if method == "Switch.Set":
                on = params.get("on") == "true"
                self.output = on
                if on and "toggle_after" in params:
                    self.timerStartedAt, self.timerDuration = self.clock(), float(params["toggle_after"])
                else:
                    self.timerStartedAt = self.timerDuration = None
                return 200, {"was_on": not on}
            if method == "PLUGS_UI.SetConfig":
                self.uiConfig = json.loads(params["config"])
                return 200, {"restart_required": False}
            memory = self.__memoryRpc(method, params)
            if memory is not None:
                return memory
            if method == "Switch.GetStatus":
                status = {"id": 0, "source": "http", "output": self.output,
                          "apower": self.lampWatts if self.output else 0.0}
                if self.timerDuration is not None:
                    status["timer_started_at"] = self.timerStartedAt
                    status["timer_duration"] = self.timerDuration
                return 200, status
        return 404, {"code": 404, "message": "No handler for %s" % method}

    def __memoryRpc(self, method, params):
        # The plug-memory calls: (status, body) or None when `method` is none of them. POST params arrive as JSON
        # values; GET params as strings.
        if method == "KVS.Set":
            value = params["value"]
            if len(json.dumps(value)) - 2 > 253:
                return 200, {"error": {"code": -103, "message": "Invalid argument 'value': length should be less than 255!"}}
            self.kvs[params["key"]] = value
            return 200, {"etag": "x", "rev": len(self.kvs)}
        if method == "KVS.Get":
            if params["key"] not in self.kvs:
                return 200, {"error": {"code": -105, "message": "Argument 'key', value '%s' not found!" % params["key"]}}
            return 200, {"etag": "x", "value": self.kvs[params["key"]]}
        if method == "KVS.Delete":
            if self.kvs.pop(params["key"], None) is None:
                return 200, {"error": {"code": -105, "message": "not found"}}
            return 200, {"rev": len(self.kvs)}
        if method == "KVS.List":
            prefix = (params.get("match") or "*").rstrip("*")
            return 200, {"keys": {k: {"etag": "x"} for k in self.kvs if k.startswith(prefix)}, "rev": len(self.kvs)}
        if method == "Script.List":
            return 200, {"scripts": [{"id": sid, "name": e["name"], "enable": False, "running": False}
                                     for sid, e in sorted(self.scripts.items())]}
        if method == "Script.Create":
            sid = self.nextScriptId
            self.nextScriptId += 1
            self.scripts[sid] = {"name": params.get("name"), "code": ""}
            return 200, {"id": sid}
        if method == "Script.PutCode":
            entry = self.scripts[int(params["id"])]
            code = (entry["code"] if params.get("append") else "") + params["code"]
            if len(code.encode()) > 65535:
                return 200, {"error": {"code": -103, "message": "Invalid argument 'code': Script length exceeded 65535 bytes limit!"}}
            self.fsFree -= len(code.encode()) - len(entry["code"].encode())
            entry["code"] = code
            return 200, {"len": len(code.encode())}
        if method == "Script.GetCode":
            data = self.scripts[int(params["id"])]["code"].encode()
            offset = int(params.get("offset", 0))
            if "len" not in params:
                return 200, {"error": {"code": -1, "message": "the fake refuses a whole-slot read (the real plug reboots)"}}
            piece = data[offset:offset + int(params["len"])]
            return 200, {"data": piece.decode(), "left": max(0, len(data) - offset - len(piece))}
        if method == "Script.Delete":
            entry = self.scripts.pop(int(params["id"]), None)
            if entry is not None:
                self.fsFree += len(entry["code"].encode())
            return 200, None
        if method == "Sys.GetStatus":
            return 200, {"fs_size": 458752, "fs_free": self.fsFree, "kvs_rev": len(self.kvs)}
        if method == "Switch.SetConfig":
            config = params["config"] if isinstance(params["config"], dict) else json.loads(params["config"])
            self.switchConfig.update(config)
            return 200, {"restart_required": False}
        if method == "Switch.GetConfig":
            return 200, dict(self.switchConfig, id=0)
        if method == "Shelly.SetAuth":
            self.authHa1 = params.get("ha1")
            return 200, None
        return None

    def __deviceInfo(self):
        return {"name": None, "id": self.REALM, "mac": self.mac, "model": "SNPL-00112EU", "gen": self.gen,
                "ver": "1.3.3", "app": "PlusPlugS", "auth_en": self.password is not None,
                "auth_domain": self.REALM if self.password else None}

    # --- auth --------------------------------------------------------------------------------------------
    def __authorized(self, header, path, method="GET"):
        if self.password is None:
            return True
        if not header.startswith("Digest "):
            return False
        fields = dict(re.findall(r'(\w+)="?([^",]*)"?', header))
        if fields.get("algorithm", "").upper() != "SHA-256":
            return False
        sha = lambda text: hashlib.sha256(text.encode()).hexdigest()
        ha1 = sha("admin:%s:%s" % (self.REALM, self.password))
        ha2 = sha("%s:%s" % (method, fields.get("uri", "")))
        expected = sha("%s:%s:%s:%s:%s:%s" % (ha1, fields.get("nonce"), fields.get("nc"), fields.get("cnonce"),
                                             fields.get("qop"), ha2))
        return fields.get("uri") == path and fields.get("response") == expected

    def __challenge(self):
        return 'Digest qop="auth", realm="%s", nonce="%s", algorithm=SHA-256' % (self.REALM, self.__nonce)

    def __handlerClass(self, server):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if server.silent:
                    time.sleep(3.0)
                    return
                if server.dark:
                    self.close_connection = True
                    self.connection.close()
                    return
                url = urllib.parse.urlparse(self.path)
                if url.path == "/shelly":
                    return self.__send(200, server._FakeShellyServer__deviceInfo())
                if not url.path.startswith("/rpc/"):
                    return self.__send(404, {"code": 404})
                if not server._FakeShellyServer__authorized(self.headers.get("Authorization", ""), self.path):
                    return self.__send(401, {"code": 401}, {"WWW-Authenticate": server._FakeShellyServer__challenge()})
                params = dict(urllib.parse.parse_qsl(url.query))
                status, body = server._FakeShellyServer__rpc(url.path[len("/rpc/"):], params)
                self.__send(status, body)

            def do_POST(self):
                # JSON-RPC over POST /rpc (the plug store's transport). Body {"id", "method", "params"}; the answer
                # is the JSON-RPC envelope {"id", "src", "result"} or {..., "error"} — always HTTP 200, like the plug.
                if server.dark:
                    self.close_connection = True
                    self.connection.close()
                    return
                length = int(self.headers.get("Content-Length") or 0)
                request = json.loads(self.rfile.read(length) or b"{}")
                if self.path != "/rpc":
                    return self.__send(404, {"code": 404})
                if not server._FakeShellyServer__authorized(self.headers.get("Authorization", ""), self.path, "POST"):
                    return self.__send(401, {"code": 401}, {"WWW-Authenticate": server._FakeShellyServer__challenge()})
                status, body = server._FakeShellyServer__rpc(request.get("method"), request.get("params") or {})
                if status != 200:
                    return self.__send(200, {"id": request.get("id"), "src": server.REALM,
                                             "error": {"code": status, "message": body.get("message")}})
                if isinstance(body, dict) and "error" in body:
                    return self.__send(200, {"id": request.get("id"), "src": server.REALM, "error": body["error"]})
                self.__send(200, {"id": request.get("id"), "src": server.REALM, "result": body})

            def __send(self, status, body, headers=None):
                payload = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                for key, value in (headers or {}).items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(payload)

        return Handler


class FakeClock:
    """Manually advanced monotonic clock for the fake plug and LampService tests."""

    def __init__(self, start=1000.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds
