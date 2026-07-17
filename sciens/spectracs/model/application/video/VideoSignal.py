from PySide6.QtCore import QObject
from PySide6.QtGui import QImage

class VideoSignal(QObject):
    image:QImage
    currentFrameIndex:int
    framesCount:int
    # True only for frames emitted DURING the auto-exposure sweep (live preview). Consumers that feed a capture
    # burst must NOT treat these as the latest capturable frame (SPEC_capture_quality.md §14.6 drop logic).
    isPreview:bool = False



