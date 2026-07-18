import importlib


class PluginEntry:
    """One plugin the host knows about. LAZY by design: it carries the codeRef string + a display title,
    and the class is imported only on resolve(). `benchOnly` marks a plugin the measurement bench may run
    but that is never a valid end-user DB binding (the Dev plugin). `version` is None for built-ins; B6
    will fill it for DB-delivered plugins, where identity is (codeRef, version)."""

    def __init__(self, codeRef: str, title: str, benchOnly: bool = False, version: str = None):
        self.codeRef = codeRef
        self.title = title
        self.benchOnly = benchOnly
        self.version = version


# Canonical codeRefs for the built-in plugins the app ships — the SINGLE source of truth for these strings.
# Everyone that used to hard-code them (the bench list, the dev-login bypass, the engine) now goes through
# this registry, retiring the four scattered, drift-prone copies (one of which was a stale, broken string).
# codeRef = "package.module.ClassName" — see PluginRegistry.resolve.
PUMPKIN_OIL_CODE_REF = "sciens.spectracs.plugins.pumpkin.PumpkinOilPlugin.PumpkinOilPlugin"
DEV_CODE_REF = "sciens.spectracs.plugins.dev.DevSpectralPlugin.DevSpectralPlugin"


class PluginRegistry:
    """The one place that answers "which plugins exist?" (the bench selector) and "give me the plugin for
    THIS codeRef" (the workflow engine, from the logged-in binding) — SPEC_plugin_distribution.md §8 A1.

    LAZY: built-in entries hold codeRef strings, not imported classes, so the app does not import every
    plugin at boot and — crucially — this is the SAME shape B6's DB-delivered plugins must take (codeRef +
    source, exec'd on demand). B6 appends DB entries to this list without reshaping anything.

    The `title` on each entry duplicates the class's `title` on purpose (so the selector needs no import);
    the resolve-all guard test asserts they stay equal, which also closes the codeRef-typo drift for good.
    """

    __BUILTINS = [
        PluginEntry(DEV_CODE_REF, "Measurement bench (dev)", benchOnly=True),
        PluginEntry(PUMPKIN_OIL_CODE_REF, "Pumpkin-seed-oil colour QM"),
    ]

    @staticmethod
    def entries(includeBenchOnly: bool = True):
        return [e for e in PluginRegistry.__BUILTINS if includeBenchOnly or not e.benchOnly]

    @staticmethod
    def codeRefs(includeBenchOnly: bool = True):
        return [e.codeRef for e in PluginRegistry.entries(includeBenchOnly)]

    @staticmethod
    def find(codeRef: str):
        for entry in PluginRegistry.__BUILTINS:
            if entry.codeRef == codeRef:
                return entry
        return None

    @staticmethod
    def listAll(includeDb: bool = True, includeBenchOnly: bool = True):
        """Enumeration for the bench selector (B6.1): the built-in entries PLUS one entry per DB-published
        `(codeRef, version)` row from `listPlugins()`. Server-down / logged-out yields an empty DB list, so the
        bench degrades to built-ins only — `entries()` stays a pure static (never touches the server) for the
        callers that must stay offline (the dev-login bypass). Only the bench calls this."""
        result = list(PluginRegistry.entries(includeBenchOnly))
        if not includeDb:
            return result
        from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
        for row in (SpectracsPyServerClient().listPlugins() or []):
            result.append(PluginEntry(row.get("codeRef"), row.get("title") or row.get("codeRef"),
                                      version=row.get("version")))
        return result

    @staticmethod
    def resolve(codeRef: str, version: str = None):
        """The single owner of "codeRef -> plugin instance". Dispatch keys on the assigned ROW'S SEALEDNESS
        (SPEC_plugin_distribution.md §8, B6.4 / D-shadow = (b)), NOT on whether the codeRef is a built-in:

          - `version is None`         -> the shipped BUILT-IN (dev bench, unassigned serial): no server fetch;
          - a SEALED row (has source) -> VERIFY the signature over the tuple against the shipped TRUSTED_KEYS,
                                          SDK-check, then exec the source (a real distributed version — B3);
          - an UNSEALED/bare row      -> the BUILT-IN (a bare/seed row is a "use the shipped copy" pointer);
          - fetch failed (offline)    -> the BUILT-IN if shipped, else error.

        So a published sealed row OVERRIDES the built-in, while the seed's bare rows and offline both fall back
        to it — which is why the seed needs no change and the F16 bootstrap gap dissolves. Heavy imports stay
        local so importing this module stays cheap (the dev-login bypass references only the codeRef constants)."""
        if version is None:
            return PluginRegistry._resolveBuiltin(codeRef)
        row = PluginRegistry._fetchDbRow(codeRef, version)
        if not row or not row.get("ok") or not row.get("source"):
            # offline, unknown version, or a bare/unsealed row -> the shipped built-in is the fallback.
            if PluginRegistry.find(codeRef) is not None:
                return PluginRegistry._resolveBuiltin(codeRef)
            raise ValueError(
                "plugin %s %s is not loadable (no sealed source) and has no built-in fallback" % (codeRef, version))
        return PluginRegistry._resolveDbPluginFromRow(codeRef, row)

    @staticmethod
    def _resolveBuiltin(codeRef: str):
        from sciens.spectracs.plugin_sdk.version import checkSdkCompatible
        moduleName, className = codeRef.rsplit(".", 1)
        module = importlib.import_module(moduleName)
        plugin = getattr(module, className)()
        checkSdkCompatible(plugin)
        return plugin

    @staticmethod
    def _fetchDbRow(codeRef: str, version: str):
        """The sealed row for (codeRef, version) over the Pyro RPC, or None/{'ok': False} when the server is
        unreachable — the caller treats either as "fall back to the built-in"."""
        from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
        return SpectracsPyServerClient().getPluginSource(codeRef, version)

    @staticmethod
    def _resolveDbPluginFromRow(codeRef: str, row: dict):
        """A SEALED row -> verify tuple -> SDK-check -> exec source as the codeRef module -> getattr class ->
        instantiate. NEVER exec unverified or SDK-incompatible source: both checks run BEFORE exec."""
        import importlib.util
        from sciens.spectracs.plugin_sdk.version import checkSdkCompatibleVersion
        from sciens.spectracs.logic.security.PluginSignatureUtil import verifySealed, PluginSignatureError
        from sciens.spectracs.logic.security.TrustedKeys import TRUSTED_KEYS

        if not verifySealed(row["codeRef"], row["version"], row["targetSdkVersion"], row["source"],
                            row["signature"], row["keyId"], TRUSTED_KEYS):
            raise PluginSignatureError(
                "signature verification FAILED for %s %s" % (codeRef, row.get("version")))

        checkSdkCompatibleVersion(row["targetSdkVersion"], row.get("title") or codeRef)

        moduleName, className = codeRef.rsplit(".", 1)
        module = importlib.util.module_from_spec(importlib.util.spec_from_loader(moduleName, loader=None))
        exec(compile(row["source"], moduleName, "exec"), module.__dict__)
        return getattr(module, className)()
