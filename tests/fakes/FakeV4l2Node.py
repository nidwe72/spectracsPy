"""A fake /dev/videoN for LinuxUvcControls — the ELP 32e4:8830 as V4L2 describes it (Windows spec §11c.11, run 2).

`state` starts as the probe found the camera: the values a previous measurement session LEFT there (WB 6500 manual,
backlight 0, exposure 90), not the firmware defaults — which is exactly why every open must write every control.
"""
from sciens.spectracs.logic.application.video.capture.LinuxUvcControls import CONTROL_IDS
from sciens.spectracs.plugin_sdk import CameraControl as C

# control: (type, min, max, step, default, leftInCamera)    type 1 int, 2 bool, 3 menu
ELP = {
    C.BRIGHTNESS: (1, -64, 64, 1, 0, 0), C.CONTRAST: (1, 0, 64, 1, 32, 32), C.SATURATION: (1, 0, 128, 1, 75, 75),
    C.HUE: (1, -40, 40, 1, 0, 0), C.WHITE_BALANCE_AUTO: (2, 0, 1, 1, 1, 0), C.GAMMA: (1, 72, 500, 1, 100, 100),
    C.GAIN: (1, 0, 100, 1, 0, 0), C.POWER_LINE_FREQUENCY: (3, 0, 2, 1, 1, 1),
    C.WHITE_BALANCE_KELVIN: (1, 2800, 6500, 1, 4600, 6500), C.SHARPNESS: (1, 0, 6, 1, 3, 3),
    C.BACKLIGHT: (1, 0, 2, 1, 1, 0), C.AUTO_EXPOSURE: (3, 0, 3, 1, 3, 1), C.EXPOSURE: (1, 1, 5000, 1, 78, 90),
    C.DYNAMIC_FRAMERATE: (2, 0, 1, 1, 0, 0),
}
MENUS = {CONTROL_IDS[C.AUTO_EXPOSURE]: {1: "Manual Mode", 3: "Aperture Priority Mode"},
         CONTROL_IDS[C.POWER_LINE_FREQUENCY]: {0: "Disabled", 1: "50 Hz", 2: "60 Hz"}}


class FakeV4l2Node:
    def __init__(self, ignore=(), missing=()):
        self.table = {CONTROL_IDS[control]: entry for control, entry in ELP.items() if control not in missing}
        self.state = {controlId: entry[5] for controlId, entry in self.table.items()}
        self.ignore = {CONTROL_IDS[control] for control in ignore}      # SET_CUR accepted, value kept (a stuck camera)
        self.writes = []
        self.closed = False

    def queryControl(self, controlId):
        entry = self.table.get(controlId)
        if entry is None:
            return None
        kind, low, high, step, default, _ = entry
        return {"type": kind, "min": low, "max": high, "step": step, "default": default, "flags": 0}

    def queryMenu(self, controlId, index):
        return MENUS.get(controlId, {}).get(index)

    def get(self, controlId):
        return self.state.get(controlId)

    def set(self, controlId, value):
        if controlId not in self.table:
            return "EINVAL"
        self.writes.append((controlId, value))
        if controlId not in self.ignore:
            self.state[controlId] = value
        return None

    def close(self):
        self.closed = True

    def written(self, control):
        return [value for controlId, value in self.writes if controlId == CONTROL_IDS[control]]
