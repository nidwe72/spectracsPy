"""Does the app reach the lamp plug and can it switch it? (SPEC_lamp_switch.md, before step 1.)

Switches the Shelly Plus Plug S on for 3 s and off for 3 s, three times, and prints what the plug reports
after each switch (output, apower). With the Yuji in the socket, `on` should read ~10 W once the meter has
caught up; ~0 W means the switch on the E27 socket is off.

Every `on` carries `toggle_after` as a dead-man, so even a killed script leaves the lamp dark within seconds;
the final `off` runs in `finally`. stdlib only, no password (the plug has none yet).

    python3 diagnostics/lamp_plug_blink.py [host] [--cycles N] [--on S] [--off S]
    python3 diagnostics/lamp_plug_blink.py [host] --timer-check

--timer-check verifies the timer semantics SPEC_lamp_switch.md §15.3 builds on (P0, first run 2026-10-02 on
fw 1.3.3: all five held; apower reads 0.0 W at 1 s and 11.2 W at 2 s):
  a) on + toggle_after reports timer_started_at / timer_duration; apower latency at 1/2/3 s
  c) a repeated on WITH toggle_after restarts the timer
  d) an on WITHOUT toggle_after cancels the running timer
  b) off clears a pending timer
  e) toggle_after really switches off
"""
import argparse
import json
import time
import urllib.request

DEFAULT_HOST = "192.168.1.123"   # Edwin's plug on Sciens2G6971 (2026-10-02)


def rpc(host, method, **params):
    query = "&".join(f"{k}={str(v).lower() if isinstance(v, bool) else v}" for k, v in params.items())
    url = f"http://{host}/rpc/{method}" + (f"?{query}" if query else "")
    with urllib.request.urlopen(url, timeout=3) as response:
        return json.loads(response.read().decode())


def report(host, label, t0):
    status = rpc(host, "Switch.GetStatus", id=0)
    print(f"{time.monotonic() - t0:6.1f}s  {label:<4}  output={status['output']!s:<5}  apower={status['apower']:5.1f} W")


def timer_check(host):
    def show(label):
        status = rpc(host, "Switch.GetStatus", id=0)
        fields = {key: status.get(key) for key in ("output", "apower", "timer_started_at", "timer_duration")}
        print(f"{label:<34} {fields}")
        return status

    try:
        rpc(host, "Switch.Set", id=0, on=True, toggle_after=30)
        for second in (1, 2, 3):
            time.sleep(1)
            show(f"a) on + {second} s")
        started = show("   timer before repeat")["timer_started_at"]
        time.sleep(1)
        rpc(host, "Switch.Set", id=0, on=True, toggle_after=30)
        restarted = show("c) repeat on with toggle_after")["timer_started_at"]
        print(f"   -> timer restarted: {restarted != started}")
        rpc(host, "Switch.Set", id=0, on=True)
        print(f"   -> d) on without toggle_after cancels: {show('d) on without toggle_after').get('timer_duration') is None}")
        rpc(host, "Switch.Set", id=0, on=True, toggle_after=30)
        rpc(host, "Switch.Set", id=0, on=False)
        print(f"   -> b) off clears the timer: {show('b) off after a timed on').get('timer_duration') is None}")
        rpc(host, "Switch.Set", id=0, on=True, toggle_after=4)
        time.sleep(6)
        print(f"   -> e) toggle_after switched off: {not show('e) toggle_after=4, after 6 s')['output']}")
    finally:
        rpc(host, "Switch.Set", id=0, on=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("host", nargs="?", default=DEFAULT_HOST)
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--on", type=float, default=3.0, help="seconds on per cycle")
    parser.add_argument("--off", type=float, default=3.0, help="seconds off per cycle")
    parser.add_argument("--timer-check", action="store_true", help="verify the toggle_after semantics instead")
    args = parser.parse_args()

    info = rpc(args.host, "Shelly.GetDeviceInfo")
    print(f"{info['id']}  {info['model']}  fw {info['ver']}  auth={info['auth_en']}")
    if args.timer_check:
        timer_check(args.host)
        return

    t0 = time.monotonic()
    try:
        for cycle in range(1, args.cycles + 1):
            print(f"-- cycle {cycle}/{args.cycles}")
            rpc(args.host, "Switch.Set", id=0, on=True, toggle_after=int(args.on) + 5)
            time.sleep(args.on)
            report(args.host, "on", t0)
            rpc(args.host, "Switch.Set", id=0, on=False)
            time.sleep(args.off)
            report(args.host, "off", t0)
    finally:
        rpc(args.host, "Switch.Set", id=0, on=False)


if __name__ == "__main__":
    main()
