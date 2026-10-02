"""A Shelly Gen2 plug on localhost for the lamp tests (SPEC_lamp_switch.md §11, D13) — no hardware in the suite.

Speaks the subset the app uses: GET /shelly (never authenticated), /rpc/Shelly.GetDeviceInfo,
/rpc/Switch.Set (on, toggle_after), /rpc/Switch.GetStatus. With a password it challenges exactly like the real
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
            if method == "Switch.GetStatus":
                status = {"id": 0, "source": "http", "output": self.output,
                          "apower": self.lampWatts if self.output else 0.0}
                if self.timerDuration is not None:
                    status["timer_started_at"] = self.timerStartedAt
                    status["timer_duration"] = self.timerDuration
                return 200, status
        return 404, {"code": 404, "message": "No handler for %s" % method}

    def __deviceInfo(self):
        return {"name": None, "id": self.REALM, "mac": self.mac, "model": "SNPL-00112EU", "gen": self.gen,
                "ver": "1.3.3", "app": "PlusPlugS", "auth_en": self.password is not None,
                "auth_domain": self.REALM if self.password else None}

    # --- auth --------------------------------------------------------------------------------------------
    def __authorized(self, header, path):
        if self.password is None:
            return True
        if not header.startswith("Digest "):
            return False
        fields = dict(re.findall(r'(\w+)="?([^",]*)"?', header))
        if fields.get("algorithm", "").upper() != "SHA-256":
            return False
        sha = lambda text: hashlib.sha256(text.encode()).hexdigest()
        ha1 = sha("admin:%s:%s" % (self.REALM, self.password))
        ha2 = sha("GET:%s" % fields.get("uri", ""))
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
