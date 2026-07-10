import io
import json
import os
import tempfile

import numpy as np
from PySide6.QtGui import QImage, QPixmap

from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.plugin.view.SpectrumCaptureView import SpectrumCaptureView
from sciens.spectracs.view.spectral.workflow.render.MatplotlibWorkflowRenderer import MatplotlibWorkflowRenderer


class WorkflowReportBuilder:
    # SPEC_bench_pdf_export.md §1/§5/§6 (D5/D6) — the host bridge between the workflow and the Qt-free matplotlib
    # report renderer. Runs on the host side (Qt allowed): it converts host-native QImage captures into Qt-free
    # PIL renditions the renderer can draw, produces the preview pixmaps (which ARE the PDF pages), and on Save
    # writes the matplotlib pages to a PDF and embeds — via pypdf — the whole-Workflow JSON plus each flagged
    # capture as a named /EmbeddedFiles attachment (extractable on command, §5b).
    #
    # Visible body = the isShownInReport subset (curated, grouped by phase, workflow order).
    # Hidden payload = workflow.toReportJson() (the complete machine record).

    __PHASE_LABELS = {
        SpectralWorkflowPhaseType.ACQUISITION: "Acquisition",
        SpectralWorkflowPhaseType.PROCESSING: "Processing",
        SpectralWorkflowPhaseType.EVALUATION: "Evaluation",
        SpectralWorkflowPhaseType.METADATA: "Metadata",
        SpectralWorkflowPhaseType.PUBLISHING: "Publishing",
    }

    def __init__(self, workflow, reportView):
        self.__workflow = workflow
        self.__reportView = reportView
        self.__figures = []
        self.__captures = []  # (attachmentName, pngBytes) for the flagged SpectrumCaptureViews

    def build(self):
        groups = self.__collectGroups()
        logo = self.__loadLogo()
        self.__figures = MatplotlibWorkflowRenderer().render(self.__reportView, groups, logoImage=logo)
        return self

    # --- collection: flagged items grouped by phase (workflow order); captures get a PIL rendition + name ---

    def __collectGroups(self):
        groups = []
        captureIndex = 0
        for phaseType in SpectralWorkflowPhaseType:
            phase = self.__workflow.getPhase(phaseType)
            if phase is None:
                continue
            items = []
            for step in phase.getSteps().values():
                for item in self.__stepItems(step):
                    if not getattr(item, "isShownInReport", False):
                        continue
                    if isinstance(item, SpectrumCaptureView):
                        captureIndex += 1
                        self.__prepareCapture(item, step, captureIndex)
                    items.append(item)
            if items:
                groups.append((self.__PHASE_LABELS.get(phaseType, str(phaseType)), items))
        return groups

    @staticmethod
    def __stepItems(step):
        items = []
        result = step.getEvaluationResult() if hasattr(step, "getEvaluationResult") else None
        if result is not None:
            items.extend(result.getItems())
        view = step.getView() if hasattr(step, "getView") else None
        if view is not None and hasattr(view, "isShownInReport"):  # a passive, reportable view (plot/capture)
            items.append(view)
        return items

    def __prepareCapture(self, capture, step, index):
        # Assign the /EmbeddedFiles name (role-based when known, else sequential) and derive the Qt-free PIL
        # rendition the matplotlib renderer draws + the PNG bytes pypdf attaches. `.image` is a host QImage.
        if not capture.attachmentName:
            role = step.getRole() if hasattr(step, "getRole") else None
            slug = (role or ("capture_%d" % index))
            capture.attachmentName = "capture_%s.png" % _slug(slug) if role else "capture_%d.png" % index
        pil = self.__qImageToPil(capture.image)
        if pil is None:
            return
        capture.reportImage = pil
        buffer = io.BytesIO()
        pil.convert("RGB").save(buffer, format="PNG")
        self.__captures.append((capture.attachmentName, buffer.getvalue()))

    @staticmethod
    def __qImageToPil(image):
        if image is None:
            return None
        from PIL import Image
        qimage = image if isinstance(image, QImage) else \
            (image.toImage() if isinstance(image, QPixmap) else None)
        if qimage is None:
            return None
        qimage = qimage.convertToFormat(QImage.Format.Format_RGBA8888)
        width, height = qimage.width(), qimage.height()
        pointer = qimage.constBits()
        array = np.frombuffer(pointer, np.uint8).reshape(height, qimage.bytesPerLine())
        array = array[:, :width * 4].reshape(height, width, 4)
        return Image.fromarray(array.copy(), "RGBA")

    def __loadLogo(self):
        from PIL import Image
        path = self.__resourcePath("logo.png")
        if path is None or not os.path.exists(path):
            return None
        try:
            return Image.open(path).convert("RGBA")
        except Exception:
            return None

    @staticmethod
    def __resourcePath(name):
        directory = os.path.dirname(os.path.abspath(__file__))
        while directory != os.path.dirname(directory):
            candidate = os.path.join(directory, "resource", name)
            if os.path.exists(candidate):
                return candidate
            directory = os.path.dirname(directory)
        return None

    # --- preview: figures -> QPixmaps (the preview IS the PDF, page for page) ---

    def previewPixmaps(self):
        pixmaps = []
        for figure in self.__figures:
            width, height, rgba = MatplotlibWorkflowRenderer.rasterize(figure)
            image = QImage(rgba, width, height, QImage.Format.Format_RGBA8888).copy()
            pixmaps.append(QPixmap.fromImage(image))
        return pixmaps

    def pageCount(self):
        return len(self.__figures)

    # --- save: matplotlib pages -> PDF, then pypdf embeds workflow.json + capture attachments ---

    def savePdf(self, path):
        from matplotlib.backends.backend_pdf import PdfPages
        tempPath = None
        try:
            handle, tempPath = tempfile.mkstemp(suffix=".pdf")
            os.close(handle)
            with PdfPages(tempPath) as pdf:
                for figure in self.__figures:
                    pdf.savefig(figure)
            self.__embedAttachments(tempPath, path)
        finally:
            if tempPath is not None and os.path.exists(tempPath):
                os.remove(tempPath)
        return path

    def __embedAttachments(self, sourcePdfPath, targetPath):
        from pypdf import PdfReader, PdfWriter
        writer = PdfWriter()
        writer.append(PdfReader(sourcePdfPath))
        if getattr(self.__reportView, "embedMetadata", True):
            payload = json.dumps(self.__workflow.toReportJson(), indent=2).encode("utf-8")
            writer.add_attachment("workflow.json", payload)
        for name, pngBytes in self.__captures:
            writer.add_attachment(name, pngBytes)
        with open(targetPath, "wb") as target:
            writer.write(target)


def _slug(text):
    return "".join(character if character.isalnum() else "_" for character in str(text)).strip("_").lower()
