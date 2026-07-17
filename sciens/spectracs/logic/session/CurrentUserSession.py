import os
from typing import List, Optional

from sciens.base.Singleton import Singleton


def _isDevLoginBypassEnabled() -> bool:
    return os.environ.get("SPECTRACS_DEV_LOGIN_BYPASS", "").strip().lower() in ("1", "true", "yes", "on")


class CurrentUserSession(Singleton):
    """In-memory current-user state for the app. Logged-out by default.

    No server session token (yet) — login() returns roles, logout() simply drops the state.
    """

    userId: Optional[str] = None
    username: Optional[str] = None
    roles: List[str] = []
    pluginId: Optional[str] = None            # legacy (dev-bypass only); real login resolves via serial
    pluginCodeRef: Optional[str] = None       # import path of the bound plugin — the client imports it
    spectrometerDevice: Optional[str] = None  # stable device code-name, e.g. "Virtuax"
    # Instrument bundle resolved from the user's serial at login (SPEC_connection_and_calibration_ux §4.3):
    registeredSerial: Optional[str] = None
    calibration: Optional[dict] = None        # ROI + pixel->nm coeffs dict (None if not calibrated yet)

    def login(self, loginResult: dict):
        self.userId = loginResult.get("userId")
        self.username = loginResult.get("username")
        self.roles = loginResult.get("roles") or []
        self.pluginId = loginResult.get("pluginId")
        self.pluginCodeRef = loginResult.get("pluginCodeRef")
        self.spectrometerDevice = loginResult.get("spectrometerDevice")
        self.registeredSerial = loginResult.get("registeredSerial")
        self.calibration = loginResult.get("calibration")

    def logout(self):
        self.userId = None
        self.username = None
        self.roles = []
        self.pluginId = None
        self.pluginCodeRef = None
        self.spectrometerDevice = None
        self.registeredSerial = None
        self.calibration = None

    def applyDevLoginBypassIfEnabled(self) -> bool:
        """Bring-up only (Android P4/P5): log in a synthetic dev user WITHOUT the server, so the
        virtual pipeline can be exercised on-device before the server app exists. Gated by the
        SPECTRACS_DEV_LOGIN_BYPASS env var; the plugin/device/role are env-overridable so the bound
        flow can be tuned during on-device validation. This bypass is REMOVED at P6 — see
        docs/SPEC_android_port.md decision D13. No-op (returns False) when the flag is off.
        """
        if not _isDevLoginBypassEnabled():
            return False

        # Local import to avoid a session↔model import cycle at module load.
        from sciens.spectracs.model.databaseEntity.application.user.UserRoleType import UserRoleType

        self.login({
            "userId": os.environ.get("SPECTRACS_DEV_USER_ID", "dev-user"),
            "username": os.environ.get("SPECTRACS_DEV_USERNAME", "dev"),
            "roles": [UserRoleType.MASTER_USER.value],
            "pluginId": os.environ.get("SPECTRACS_DEV_PLUGIN_ID", "pumpkin-oil"),
            "pluginCodeRef": os.environ.get(
                "SPECTRACS_DEV_PLUGIN_CODEREF",
                "sciens.spectracs.plugins.pumpkin.PumpkinOilPlugin"),
            "spectrometerDevice": os.environ.get("SPECTRACS_DEV_DEVICE", "Virtuax"),
        })
        return True

    def isLoggedIn(self) -> bool:
        return self.userId is not None

    def hasRole(self, roleName: str) -> bool:
        return roleName in self.roles

    def getPluginId(self) -> Optional[str]:
        return self.pluginId

    def getPluginCodeRef(self) -> Optional[str]:
        return self.pluginCodeRef

    def getSpectrometerDevice(self) -> Optional[str]:
        return self.spectrometerDevice

    def getRegisteredSerial(self) -> Optional[str]:
        return self.registeredSerial

    def getCalibration(self) -> Optional[dict]:
        return self.calibration
