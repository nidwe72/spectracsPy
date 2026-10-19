from typing import Optional


class ServerCompatibility:
    """App ↔ server version check (SPEC_shelly_instrument_memory.md R12 / S1b). The server reports its DB's Alembic
    revision at login; a revision that is not in the server tree this app ships means the server was migrated by
    newer code than this app knows ⇒ refuse with a clear message instead of failing later on a missing field.
    The same rule applies to an instrument copy read from the plug (S3)."""

    NEWER_SERVER = "The server is newer than this app — please update the app."
    NEWER_COPY = "The instrument data on the plug is newer than this app — please update the app."

    _known = None

    @classmethod
    def knownRevisions(cls) -> set:
        if cls._known is None:
            from sciens.spectracs.model.databaseEntity.DatabaseInitializer import getServerScriptRevisions
            cls._known = getServerScriptRevisions()
        return cls._known

    @classmethod
    def isKnown(cls, revision: Optional[str]) -> bool:
        # None = an old server that does not report a revision (or a DB without alembic_version) ⇒ accepted.
        return revision is None or revision in cls.knownRevisions()

    @classmethod
    def refusalForServer(cls, revision: Optional[str]) -> Optional[str]:
        return None if cls.isKnown(revision) else cls.NEWER_SERVER
