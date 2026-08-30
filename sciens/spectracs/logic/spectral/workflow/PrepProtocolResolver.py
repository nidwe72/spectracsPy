import os

from sciens.spectracs.model.databaseEntity.AppDataPathUtil import get_app_data_dir

FILE_NAME = "prepProtocol.txt"
ENV_NAME = "SPECTRACS_PREP_PROTOCOL"


class PrepProtocolResolver:
    """What the LAB RECIPE was for this run — resolved per run, not compiled in.

    ⛔⛔ WHY THIS EXISTS. `prepProtocol` was a hardcoded class constant on the plugin, and it went stale
    twice without anybody noticing: on 2026-08-27 the recipe became a two-stage vortex and on 2026-08-28 a
    cold ultrasonic bath and an insulated box were added, while every report still stamped
    `invert-40-after-capillaries-clear`. `SPEC_metric_research.md` §16.15 is the bill for that — the whole
    pre-vortex archive had to be set aside as a separate population, because "was it the recipe?" could not
    be answered from the record for ANY fill in it.

    ⭐ The fix is not a better constant. A constant needs a code edit and a release to change, so it will go
    stale again the next time the bench changes on a Friday evening. The recipe is now read at the START OF
    EVERY RUN from a place the operator can edit between fills:

        1. the ``SPECTRACS_PREP_PROTOCOL`` environment variable, if set and non-empty;
        2. else the first non-empty, non-``#`` line of ``prepProtocol.txt`` in the app data directory;
        3. else whatever the plugin declares — which stays the honest default for a plugin that ships one.

    ⚠ FREE-FORM ON PURPOSE. A recipe is not an enum; forcing one would just stop it being written. The one
    thing worth insisting on is that it names the parts that have actually moved: the mixing, the sonic
    step, and the stand.
    """

    @staticmethod
    def overridePath() -> str:
        return os.path.join(get_app_data_dir(), FILE_NAME)

    @classmethod
    def resolve(cls, declared=None):
        """The recipe string for a run about to start. Never raises: provenance must not break a capture."""
        environment = (os.environ.get(ENV_NAME) or "").strip()
        if environment:
            return environment
        try:
            with open(cls.overridePath(), encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        return line
        except OSError:
            # ⚠ No file, unreadable file, or no data directory at all -> fall through to the plugin's own
            # declaration. A missing override is the normal case, not an error.
            pass
        return declared
