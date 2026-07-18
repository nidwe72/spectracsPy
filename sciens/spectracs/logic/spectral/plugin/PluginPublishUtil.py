"""B4 (SPEC_plugin_distribution.md §8) — master-side publish helpers. App-tier and desktop-only.

Given a picked plugin source file, DERIVE the class name / title / targetSdkVersion by importing it on the
master's TRUSTED machine (Q5: no hand-typed values that must match the code), and enforce the
one-self-contained-module rule (Q1) as a publish-time LINT. The lint is HYGIENE, not a sandbox (§3) — with a
single trusted author it catches honest mistakes (a stray sibling import, a multi-file plugin), which is
exactly its job.
"""
import ast

from sciens.spectracs.plugin_sdk.base.SpectralPlugin import SpectralPlugin
from sciens.spectracs.plugin_sdk.version import SDK_VERSION

_PLUGIN_SDK_ROOT = "sciens.spectracs.plugin_sdk"


class PluginSourceError(Exception):
    """The picked source is not a single self-contained SpectralPlugin module (bad imports, zero or many
    plugin classes, or it failed to import). Publishing is refused BEFORE signing."""


def _forbiddenImport(moduleName: str) -> bool:
    # A plugin may import stdlib, third-party (numpy…) and plugin_sdk — but NOT app/sibling code. The only
    # allowed sciens.* import is the SDK; anything else means it is not self-contained (Q1).
    if not moduleName:
        return False
    if moduleName.split(".")[0] != "sciens":
        return False
    return not (moduleName == _PLUGIN_SDK_ROOT or moduleName.startswith(_PLUGIN_SDK_ROOT + "."))


def lintSelfContained(source: str) -> None:
    """Raise PluginSourceError if the source imports app/sibling code or uses a relative import — the
    one-importable-module rule, enforced at publish so a multi-file plugin is rejected here, never silently
    broken at load."""
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        raise PluginSourceError("source does not parse: %s" % error)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _forbiddenImport(alias.name):
                    raise PluginSourceError(
                        "a plugin may not import app/sibling code: 'import %s'" % alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                raise PluginSourceError("a plugin may not use relative imports")
            if _forbiddenImport(node.module or ""):
                raise PluginSourceError(
                    "a plugin may not import app/sibling code: 'from %s import …'" % node.module)


def inspectPluginSource(source: str) -> dict:
    """Lint, then import the source in isolation and read the single SpectralPlugin subclass it DEFINES.
    Returns {"className", "title", "targetSdkVersion"} — the values that go into the signed tuple and the row,
    derived from the code rather than hand-typed. Raises PluginSourceError on any shape problem."""
    lintSelfContained(source)
    moduleName = "sciens.spectracs.plugins._publish_inspect"
    namespace = {"__name__": moduleName}
    try:
        exec(compile(source, moduleName, "exec"), namespace)
    except Exception as error:
        raise PluginSourceError("source failed to import: %s" % error)

    classes = [obj for obj in namespace.values()
               if isinstance(obj, type) and issubclass(obj, SpectralPlugin) and obj is not SpectralPlugin
               and obj.__module__ == moduleName]
    if not classes:
        raise PluginSourceError("no SpectralPlugin subclass found in the source")
    if len(classes) > 1:
        raise PluginSourceError(
            "the source defines more than one plugin class: %s" % ", ".join(c.__name__ for c in classes))

    pluginClass = classes[0]
    title = getattr(pluginClass, "title", None)
    if not title:
        raise PluginSourceError("the plugin class does not set a `title`")
    return {"className": pluginClass.__name__, "title": title,
            "targetSdkVersion": getattr(pluginClass, "targetSdkVersion", SDK_VERSION)}


def codeRefMatchesClass(codeRef: str, className: str) -> bool:
    """D-coderef: the loader execs the source and does `getattr(module, codeRef.rsplit('.',1)[1])`, so the
    codeRef's last segment MUST equal the class name — validated at publish (fail at the master's desk, not
    at getattr on a field phone)."""
    return bool(codeRef) and bool(className) and codeRef.rsplit(".", 1)[-1] == className
