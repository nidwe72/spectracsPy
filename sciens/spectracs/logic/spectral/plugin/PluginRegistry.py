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
    def resolve(codeRef: str, version: str = None):
        """The single owner of "codeRef -> plugin instance". Dispatches (a sliver of B6):
          - a **built-in** codeRef (in this registry) -> importlib.import_module (trusted by shipping in the APK);
          - anything else -> a **DB-delivered** plugin: fetch the sealed row, VERIFY the signature over the tuple
            against the shipped TRUSTED_KEYS, SDK-check, then exec the source (B3).
        Heavy imports are local so importing this module stays cheap (the dev-login bypass references only the
        codeRef constants)."""
        entry = PluginRegistry.find(codeRef)
        if entry is not None and entry.version is None:
            return PluginRegistry._resolveBuiltin(codeRef)
        return PluginRegistry._resolveDbPlugin(codeRef, version)

    @staticmethod
    def _resolveBuiltin(codeRef: str):
        from sciens.spectracs.plugin_sdk.version import checkSdkCompatible
        moduleName, className = codeRef.rsplit(".", 1)
        module = importlib.import_module(moduleName)
        plugin = getattr(module, className)()
        checkSdkCompatible(plugin)
        return plugin

    @staticmethod
    def _resolveDbPlugin(codeRef: str, version: str):
        """Fetch -> verify tuple -> SDK-check -> exec source as the codeRef module -> getattr class ->
        instantiate. NEVER exec unverified or SDK-incompatible source: both checks run BEFORE exec."""
        import importlib.util
        from sciens.spectracs.plugin_sdk.version import checkSdkCompatibleVersion
        from sciens.spectracs.logic.security.PluginSignatureUtil import verifySealed, PluginSignatureError
        from sciens.spectracs.logic.security.TrustedKeys import TRUSTED_KEYS
        from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient

        if version is None:
            raise ValueError("a DB plugin must be resolved by (codeRef, version): %s" % codeRef)
        row = SpectracsPyServerClient().getPluginSource(codeRef, version)
        if not row or not row.get("ok"):
            raise ValueError("plugin %s %s unavailable: %s" % (codeRef, version, (row or {}).get("message")))

        if not verifySealed(row["codeRef"], row["version"], row["targetSdkVersion"], row["source"],
                            row["signature"], row["keyId"], TRUSTED_KEYS):
            raise PluginSignatureError("signature verification FAILED for %s %s" % (codeRef, version))

        checkSdkCompatibleVersion(row["targetSdkVersion"], row.get("title") or codeRef)

        moduleName, className = codeRef.rsplit(".", 1)
        module = importlib.util.module_from_spec(importlib.util.spec_from_loader(moduleName, loader=None))
        exec(compile(row["source"], moduleName, "exec"), module.__dict__)
        return getattr(module, className)()
