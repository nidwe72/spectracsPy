from typing import Dict

from PySide6.QtGui import QImage

from sciens.base.Singleton import Singleton
from sciens.spectracs.model.application.setting.virtualSpectrometer.VirtualCaptureRole import VirtualCaptureRole


class VirtualSpectrometerSettings(Singleton):
    # Holds up to three role-keyed virtual camera images (CALIBRATION / REFERENCE / SAMPLE) and an
    # `activeRole` pointer. The engine sets the active role before each serialised capture; the legacy
    # get/setVirtualCameraImage() shim serves the active role's image so VideoThread stays unchanged.
    # (SPEC_pumpkin_integration.md A.1 / D14)

    __imagesByRole: Dict[VirtualCaptureRole, QImage] = None
    __activeRole: VirtualCaptureRole = None
    __doSavePhysicallyCapturedImages: bool = False

    def __getImagesByRole(self) -> Dict[VirtualCaptureRole, QImage]:
        # Lazy init: Singleton re-runs __init__ on every construction, so state lives in lazy getters.
        if self.__imagesByRole is None:
            self.__imagesByRole = {}
        return self.__imagesByRole

    def setImage(self, role: VirtualCaptureRole, image: QImage):
        self.__getImagesByRole()[role] = image
        if self.__activeRole is None:  # first image set becomes the default active role
            self.__activeRole = role

    def getImage(self, role: VirtualCaptureRole) -> QImage:
        return self.__getImagesByRole().get(role)

    def setActiveRole(self, role: VirtualCaptureRole):
        self.__activeRole = role

    def getActiveRole(self) -> VirtualCaptureRole:
        return self.__activeRole

    # --- legacy shim (VideoThread.__captureVirtualFrame reads the ACTIVE role unchanged) ---

    def setVirtualCameraImage(self, virtualCameraImage: QImage):
        role = self.__activeRole if self.__activeRole is not None else VirtualCaptureRole.REFERENCE
        self.__activeRole = role
        self.__getImagesByRole()[role] = virtualCameraImage

    def getVirtualCameraImage(self) -> QImage:
        if self.__activeRole is None:
            return None
        return self.__getImagesByRole().get(self.__activeRole)

    def getDoSavePhysicallyCapturedImages(self) -> bool:
        return self.__doSavePhysicallyCapturedImages

    def setDoSavePhysicallyCapturedImages(self, doSavePhysicallyCapturedImages: bool):
        self.__doSavePhysicallyCapturedImages = doSavePhysicallyCapturedImages
