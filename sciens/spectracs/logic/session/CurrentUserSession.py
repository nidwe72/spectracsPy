from typing import List, Optional

from sciens.base.Singleton import Singleton


class CurrentUserSession(Singleton):
    """In-memory current-user state for the app. Logged-out by default.

    No server session token (yet) — login() returns roles, logout() simply drops the state.
    """

    userId: Optional[str] = None
    username: Optional[str] = None
    roles: List[str] = []
    pluginId: Optional[str] = None            # config binding downloaded at login (SPEC B.1a)
    pluginCodeRef: Optional[str] = None       # import path of the bound plugin — the client imports it
    spectrometerDevice: Optional[str] = None  # stable device code-name, e.g. "Virtuax"

    def login(self, loginResult: dict):
        self.userId = loginResult.get("userId")
        self.username = loginResult.get("username")
        self.roles = loginResult.get("roles") or []
        self.pluginId = loginResult.get("pluginId")
        self.pluginCodeRef = loginResult.get("pluginCodeRef")
        self.spectrometerDevice = loginResult.get("spectrometerDevice")

    def logout(self):
        self.userId = None
        self.username = None
        self.roles = []
        self.pluginId = None
        self.pluginCodeRef = None
        self.spectrometerDevice = None

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
