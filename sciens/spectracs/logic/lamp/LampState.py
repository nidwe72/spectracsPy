from enum import Enum


class LampState(str, Enum):
    # SPEC_lamp_switch.md §16.2 — the authoritative state table.
    NOT_APPLICABLE = 'NOT_APPLICABLE'   # virtual device / logged out: no icon, no line, no gate
    SEARCHING = 'SEARCHING'             # discovery running: gate closed, an on is queued
    NO_PLUG = 'NO_PLUG'                 # none found (or it needs a password we do not have): user switches at the socket
    OFF = 'OFF'
    WARMING = 'WARMING'                 # on, < warm-up seconds
    ON = 'ON'
    UNREACHABLE = 'UNREACHABLE'         # the plug stopped answering; last known state kept, no capture stop
