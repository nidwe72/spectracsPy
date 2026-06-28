from typing import List, Optional

from sciens.base.Singleton import Singleton


class CurrentUserSession(Singleton):
    """In-memory current-user state for the app. Logged-out by default.

    No server session token (yet) — login() returns roles, logout() simply drops the state.
    """

    userId: Optional[str] = None
    username: Optional[str] = None
    roles: List[str] = []

    def login(self, loginResult: dict):
        self.userId = loginResult.get("userId")
        self.username = loginResult.get("username")
        self.roles = loginResult.get("roles") or []

    def logout(self):
        self.userId = None
        self.username = None
        self.roles = []

    def isLoggedIn(self) -> bool:
        return self.userId is not None

    def hasRole(self, roleName: str) -> bool:
        return roleName in self.roles
