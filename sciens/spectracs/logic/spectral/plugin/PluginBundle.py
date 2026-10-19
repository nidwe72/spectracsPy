import importlib
import importlib.abc
import importlib.util
import os
import sys
from contextlib import contextmanager

from sciens.spectracs.logic.security import PluginBundleUtil


class PluginBundleBuilder:
    """MASTER side (SPEC_shelly_instrument_memory.md S2b): one plugin + all its module files as a signed bundle for the
    plug. A built-in plugin is collected from its package folder (the dev bench = DevSpectralPlugin + its five gauge
    views); a sealed DB row is a one-module bundle of its source."""

    @staticmethod
    def modulesOfBuiltin(codeRef: str) -> dict:
        moduleName = codeRef.rsplit(".", 1)[0]
        module = importlib.import_module(moduleName)
        package, folder = moduleName.rsplit(".", 1)[0], os.path.dirname(module.__file__)
        result = {}
        for fileName in sorted(os.listdir(folder)):
            if fileName.endswith(".py") and fileName != "__init__.py":
                with open(os.path.join(folder, fileName), encoding="utf-8") as handle:
                    result["%s.%s" % (package, fileName[:-3])] = handle.read()
        return result

    @staticmethod
    def forBuiltin(codeRef: str, version: str, targetSdkVersion, title: str = None) -> dict:
        return PluginBundleUtil.make(codeRef, version, targetSdkVersion,
                                     PluginBundleBuilder.modulesOfBuiltin(codeRef), title)

    @staticmethod
    def forSealedRow(row: dict) -> dict:
        moduleName = row["codeRef"].rsplit(".", 1)[0]
        return PluginBundleUtil.make(row["codeRef"], row["version"], row["targetSdkVersion"],
                                     {moduleName: row["source"]}, row.get("title"))

    @staticmethod
    def packSigned(bundle: dict) -> bytes:
        from sciens.spectracs.logic.security.PluginSigner import signBundle
        signature, keyId = signBundle(bundle)
        return PluginBundleUtil.pack(bundle, signature, keyId)


class _BundleFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):

    def __init__(self, modules: dict):
        self.modules = modules

    def find_spec(self, fullname, path=None, target=None):
        if fullname in self.modules:
            return importlib.util.spec_from_loader(fullname, self)
        return None

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        exec(compile(self.modules[module.__name__], module.__name__, "exec"), module.__dict__)


class PluginBundleLoader:
    """APP side (S3b): verify a bundle against the shipped master TRUSTED_KEYS, SDK-check it, and only then run it.

    Its modules are imported under their real names (the plugin imports its own gauge views absolutely) while a
    finder serves them from the bundle; around that import the app's own copies of the same names are moved aside and
    put back afterwards, so loading a bundle never replaces a module the rest of the app holds."""

    @staticmethod
    def load(envelope: dict, trustedKeys: dict = None):
        from sciens.spectracs.logic.security.PluginSignatureUtil import PluginSignatureError
        from sciens.spectracs.plugin_sdk.version import checkSdkCompatibleVersion
        if trustedKeys is None:
            from sciens.spectracs.logic.security.TrustedKeys import TRUSTED_KEYS as trustedKeys
        bundle = envelope["bundle"]
        if not PluginBundleUtil.verify(bundle, envelope.get("signature"), envelope.get("keyId"), trustedKeys):
            raise PluginSignatureError("signature verification FAILED for the plugin bundle %s %s"
                                       % (bundle.get("codeRef"), bundle.get("version")))
        checkSdkCompatibleVersion(bundle["targetSdkVersion"], bundle.get("title") or bundle["codeRef"])
        moduleName, className = bundle["codeRef"].rsplit(".", 1)
        with PluginBundleLoader.__served(bundle["modules"]):
            module = importlib.import_module(moduleName)
        return getattr(module, className)()

    @staticmethod
    @contextmanager
    def __served(modules: dict):
        finder = _BundleFinder(modules)
        displaced = {name: sys.modules.pop(name) for name in list(modules) if name in sys.modules}
        sys.meta_path.insert(0, finder)
        try:
            yield
        finally:
            sys.meta_path.remove(finder)
            for name in modules:
                sys.modules.pop(name, None)
            sys.modules.update(displaced)
