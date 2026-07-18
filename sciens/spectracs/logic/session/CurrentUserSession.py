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
    pluginVersion: Optional[str] = None       # B5.4: the EXACT bound version; None -> the shipped built-in
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
        self.pluginVersion = loginResult.get("pluginVersion")
        self.spectrometerDevice = loginResult.get("spectrometerDevice")
        self.registeredSerial = loginResult.get("registeredSerial")
        self.calibration = loginResult.get("calibration")

    def logout(self):
        self.userId = None
        self.username = None
        self.roles = []
        self.pluginId = None
        self.pluginCodeRef = None
        self.pluginVersion = None
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

        # Local imports to avoid a session↔model import cycle at module load. The plugin codeRef default
        # comes from the PluginRegistry's canonical constant (A1) — never a literal string here, which is
        # exactly the drift that left this bypass pointing at a stale, broken codeRef (F1).
        from sciens.spectracs.model.databaseEntity.application.user.UserRoleType import UserRoleType
        from sciens.spectracs.logic.spectral.plugin.PluginRegistry import PUMPKIN_OIL_CODE_REF

        self.login({
            "userId": os.environ.get("SPECTRACS_DEV_USER_ID", "dev-user"),
            "username": os.environ.get("SPECTRACS_DEV_USERNAME", "dev"),
            "roles": [UserRoleType.MASTER_USER.value],
            "pluginId": os.environ.get("SPECTRACS_DEV_PLUGIN_ID", "pumpkin-oil"),
            "pluginCodeRef": os.environ.get("SPECTRACS_DEV_PLUGIN_CODEREF", PUMPKIN_OIL_CODE_REF),
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

    def getPluginVersion(self) -> Optional[str]:
        # None for the dev-bypass and any built-in binding -> resolve() takes the built-in branch (no fetch).
        return self.pluginVersion

    def getSpectrometerDevice(self) -> Optional[str]:
        return self.spectrometerDevice

    def getRegisteredSerial(self) -> Optional[str]:
        return self.registeredSerial

    def getCalibration(self) -> Optional[dict]:
        return self.calibration
