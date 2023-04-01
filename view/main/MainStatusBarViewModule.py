from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QProgressBar

from PySide6 import QtCore

from chromos.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from chromos.spectracs.model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal

class MainStatusBarViewModule(QWidget):

    pixmap=None
    painter=None
    svgRenderer=None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFixedHeight(100)

        layout=QGridLayout()
        layout.setContentsMargins(0,0,0,0)
        self.setLayout(layout)

        self.label=QLabel()

        self.pixmap = QPixmap(480,100)
        self.pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        self.painter=QPainter(self.pixmap)

        self.svgRenderer = QSvgRenderer()
        self.svgRenderer.load(bytearray(self.logo_png,'utf-8'))

        self.svgRenderer.render(self.painter,self.pixmap.rect())
        self.label.setPixmap(self.pixmap)
        self.label.setScaledContents(True)
        self.label.setMinimumWidth(int(480 * 1.5))

        layout.addWidget(self.label,0,0, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        self.progressBar=QProgressBar(self)
        self.progressBar.setMinimumWidth(int(480 * 1.5))
        self.resetProgressBar()

        layout.addWidget(self.progressBar, 1, 0, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        ApplicationContextLogicModule().getApplicationSignalsProvider().applicationStatusSignal.connect(
            self.handleApplicationStatusSignal)

    def resetProgressBar(self):
        self.progressBar.setValue(0)
        self.progressBar.setFormat('ready for action...')

    def handleApplicationStatusSignal(self,applicationStatusSignal:ApplicationStatusSignal):

        if applicationStatusSignal.isStatusReset:
            self.resetProgressBar()
        else:
            self.progressBar.setFormat(applicationStatusSignal.text)
            percents = applicationStatusSignal.currentStepIndex / float(applicationStatusSignal.stepsCount) * 100.0
            self.progressBar.setValue(percents)


    logo_png='''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!-- Created with Inkscape (http://www.inkscape.org/) -->

<svg
   xmlns:dc="http://purl.org/dc/elements/1.1/"
   xmlns:cc="http://creativecommons.org/ns#"
   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
   xmlns:svg="http://www.w3.org/2000/svg"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   width="160.33255mm"
   height="15.725352mm"
   viewBox="0 0 160.33255 15.725352"
   version="1.1"
   id="svg8"
   inkscape:version="0.92.5 (2060ec1f9f, 2020-04-08)"
   sodipodi:docname="logo2.svg">
  <defs
     id="defs2">
    <clipPath
       id="clipPath835"
       clipPathUnits="userSpaceOnUse">
      <path
         style="clip-rule:evenodd"
         inkscape:connector-curvature="0"
         id="path833"
         d="M 0,0.028 H 595.275 V 841.889 H 0 Z" />
    </clipPath>
    <clipPath
       id="clipPath901"
       clipPathUnits="userSpaceOnUse">
      <path
         style="clip-rule:evenodd"
         inkscape:connector-curvature="0"
         id="path899"
         d="M 0,0.028 H 595.275 V 841.889 H 0 Z" />
    </clipPath>
  </defs>
  <sodipodi:namedview
     id="base"
     pagecolor="#ffffff"
     bordercolor="#666666"
     borderopacity="1.0"
     inkscape:pageopacity="0.0"
     inkscape:pageshadow="2"
     inkscape:zoom="0.7"
     inkscape:cx="-188.67738"
     inkscape:cy="-15.947101"
     inkscape:document-units="mm"
     inkscape:current-layer="layer1"
     showgrid="false"
     inkscape:window-width="1920"
     inkscape:window-height="1015"
     inkscape:window-x="1920"
     inkscape:window-y="0"
     inkscape:window-maximized="1"
     fit-margin-top="0"
     fit-margin-left="0"
     fit-margin-right="0"
     fit-margin-bottom="0" />
  <metadata
     id="metadata5">
    <rdf:RDF>
      <cc:Work
         rdf:about="">
        <dc:format>image/svg+xml</dc:format>
        <dc:type
           rdf:resource="http://purl.org/dc/dcmitype/StillImage" />
        <dc:title></dc:title>
      </cc:Work>
    </rdf:RDF>
  </metadata>
  <g
     inkscape:label="Layer 1"
     inkscape:groupmode="layer"
     id="layer1"
     transform="translate(-25.285254,-74.246968)">
    <g
       style="opacity:0.98000004;fill:none;stroke:#33663d;stroke-opacity:1"
       id="g903"
       transform="matrix(0.35277777,0,0,-0.35277777,-0.21201678,347.18298)"
       inkscape:export-xdpi="96"
       inkscape:export-ydpi="96"
       inkscape:export-filename="/home/nidwe/development/spectracs/spectracsPy/view/main/logo.png">
      <g
         aria-label="SPECTRACS"
         transform="matrix(0.96592805,0,-0.25881076,-0.96592805,66.5,730.789)"
         style="font-variant:normal;font-weight:500;font-size:82.82190704px;font-family:'Anoxic SC';-inkscape-font-specification:AnoxicSC-Medium;writing-mode:lr-tb;fill:none;fill-opacity:1;fill-rule:nonzero;stroke:#33663d;stroke-width:2.66666007;stroke-linecap:butt;stroke-linejoin:miter;stroke-miterlimit:10;stroke-dasharray:none;stroke-opacity:1"
         id="text907">
        <path
           d="m 17.558244,-42.818926 h 20.374189 q 3.478521,0 3.478521,3.47852 0,3.47852 -3.478521,3.47852 H 18.055176 q -2.484657,0 -3.89263,1.325151 -1.32515,1.32515 -1.32515,3.892629 0,2.401836 1.242328,3.809808 1.325151,1.325151 3.975452,1.325151 H 32.1349 q 5.714712,0 9.276054,3.395698 3.561342,3.395698 3.561342,9.11041 0,2.815944 -0.993863,5.2177797 -0.911041,2.4018353 -2.650301,4.1410954 -1.656439,1.73926 -4.058274,2.73312292 Q 34.950845,0 32.1349,0 H 10.021451 q -3.3956984,0 -3.3956984,-3.4785201 0,-3.4785201 3.3956984,-3.4785201 h 21.782161 q 2.650301,0 4.141096,-1.6564381 1.490794,-1.6564377 1.490794,-4.3895607 0,-5.549068 -5.63189,-5.549068 H 17.558244 q -2.733123,0 -4.969314,-0.828219 -2.236192,-0.911041 -3.8926298,-2.484657 -1.5736162,-1.656439 -2.4846572,-3.89263 -0.9110409,-2.236192 -0.9110409,-4.886493 0,-2.650301 0.9110409,-4.886492 0.911041,-2.236192 2.4846572,-3.809808 1.6564378,-1.656438 3.8926298,-2.567479 2.236191,-0.911041 4.969314,-0.911041 z"
           style="stroke:#33663d;stroke-opacity:1"
           id="path985"
           inkscape:connector-curvature="0" />
        <path
           d="m 63.690046,-42.818926 h 24.018353 q 6.54293,0 10.021451,3.395698 3.47852,3.395698 3.47852,9.938629 0,6.625753 -3.47852,10.187095 -3.478521,3.561342 -10.021451,3.561342 H 75.864866 q -3.395698,0 -3.395698,-3.561342 0,-3.395699 3.395698,-3.395699 h 11.098136 q 3.726985,0 5.134958,-1.407972 1.407972,-1.490794 1.407972,-5.21778 0,-1.904904 -0.331287,-3.147233 -0.248466,-1.32515 -0.993863,-2.070547 -0.745397,-0.745397 -2.070548,-0.993863 -1.242328,-0.331288 -3.147232,-0.331288 H 67.499853 v 32.5490097 q 0,3.72698584 -3.975451,3.72698584 -3.726986,0 -3.726986,-3.72698584 V -38.926296 q 0,-3.89263 3.89263,-3.89263 z"
           style="stroke:#33663d;stroke-opacity:1"
           id="path987"
           inkscape:connector-curvature="0" />
        <path
           d="M 115.78502,-3.8926296 V -38.926296 q 0,-3.89263 3.89263,-3.89263 h 30.14718 q 3.47852,0 3.47852,3.47852 0,3.47852 -3.47852,3.47852 h -26.33737 v 28.9048458 h 26.66865 q 3.47852,0 3.47852,3.4785201 Q 153.63463,0 150.15611,0 h -30.47846 q -3.89263,0 -3.89263,-3.8926296 z M 131.85247,-25.17786 h 13.49997 q 3.31288,0 3.31288,3.312877 0,3.395698 -3.31288,3.395698 h -13.49997 q -3.31287,0 -3.31287,-3.395698 0,-3.312877 3.31287,-3.312877 z"
           style="stroke:#33663d;stroke-opacity:1"
           id="path989"
           inkscape:connector-curvature="0" />
        <path
           d="m 175.58244,-42.818926 h 27.99381 q 3.3957,0 3.3957,3.47852 0,3.47852 -3.3957,3.47852 h -27.99381 v 28.9048458 h 29.07049 q 3.3957,0 3.3957,3.4785201 Q 208.04863,0 204.65293,0 h -29.07049 q -3.72698,0 -5.71471,-1.9877258 -1.98772,-1.9877257 -1.98772,-5.7147116 V -35.116489 q 0,-3.726985 1.98772,-5.714711 1.98773,-1.987726 5.71471,-1.987726 z"
           style="stroke:#33663d;stroke-opacity:1"
           id="path991"
           inkscape:connector-curvature="0" />
        <path
           d="m 214.34309,-39.340406 q 0,-3.47852 3.47852,-3.47852 h 35.19931 q 3.3957,0 3.3957,3.47852 0,3.47852 -3.3957,3.47852 h -35.19931 q -3.47852,0 -3.47852,-3.47852 z m 17.14414,35.9447078 V -27.662517 q 0,-3.726986 3.72698,-3.726986 h 0.24847 q 3.72698,0 3.72698,3.726986 v 24.2668188 q 0,3.80980774 -3.97545,3.80980774 -3.72698,0 -3.72698,-3.80980774 z"
           style="stroke:#33663d;stroke-opacity:1"
           id="path993"
           inkscape:connector-curvature="0" />
        <path
           d="m 266.43806,-38.926296 q 0,-3.89263 3.89263,-3.89263 h 22.36191 q 6.70858,0 10.1871,3.47852 3.47852,3.395698 3.47852,9.938629 0,4.886493 -2.48466,8.199369 -2.48466,3.230054 -6.95704,4.638027 l 9.35888,12.2576418 q 3.56134,4.72084874 -2.56748,4.72084874 -3.14723,0 -4.88649,-2.40183534 L 288.55151,-15.818984 h -6.12882 q -3.31288,0 -3.31288,-3.561342 0,-3.395698 3.31288,-3.395698 h 9.4417 q 3.14723,0 4.96931,-1.73926 1.82208,-1.822082 1.82208,-4.969315 0,-3.561342 -1.49079,-4.969314 -1.40797,-1.407973 -5.3006,-1.407973 H 274.1405 v 32.4661878 q 0,3.80980774 -3.89263,3.80980774 -3.80981,0 -3.80981,-3.80980774 z"
           style="stroke:#33663d;stroke-opacity:1"
           id="path995"
           inkscape:connector-curvature="0" />
        <path
           d="m 318.20176,-4.472383 17.30978,-35.19931 q 1.65644,-3.395699 5.46624,-3.395699 3.72699,0 5.38343,3.395699 l 17.30978,35.19931 q 2.48465,4.88649254 -2.98159,4.88649254 h -0.0828 q -2.81595,0 -3.97546,-2.48465724 l -3.89263,-7.9509033 h -13.49997 q -2.40183,0 -3.23005,-1.242328 -0.82822,-1.242329 0.33129,-3.395699 1.1595,-2.236191 3.56134,-2.236191 h 9.60734 l -8.53066,-17.558244 -15.73616,32.3833653 q -1.15951,2.48465724 -3.97545,2.48465724 -5.54907,0 -3.06441,-4.88649254 z"
           style="stroke:#33663d;stroke-opacity:1"
           id="path997"
           inkscape:connector-curvature="0" />
        <path
           d="m 385.03903,-42.818926 h 27.99381 q 3.39569,0 3.39569,3.47852 0,3.47852 -3.39569,3.47852 h -27.99381 v 28.9048458 h 29.07049 q 3.3957,0 3.3957,3.4785201 Q 417.50522,0 414.10952,0 h -29.07049 q -3.72698,0 -5.71471,-1.9877258 -1.98773,-1.9877257 -1.98773,-5.7147116 V -35.116489 q 0,-3.726985 1.98773,-5.714711 1.98773,-1.987726 5.71471,-1.987726 z"
           style="stroke:#33663d;stroke-opacity:1"
           id="path999"
           inkscape:connector-curvature="0" />
        <path
           d="m 440.52971,-42.818926 h 20.37419 q 3.47852,0 3.47852,3.47852 0,3.47852 -3.47852,3.47852 h -19.87726 q -2.48466,0 -3.89263,1.325151 -1.32515,1.32515 -1.32515,3.892629 0,2.401836 1.24233,3.809808 1.32515,1.325151 3.97545,1.325151 h 14.07973 q 5.71471,0 9.27605,3.395698 3.56134,3.395698 3.56134,9.11041 0,2.815944 -0.99386,5.2177797 -0.91104,2.4018353 -2.6503,4.1410954 -1.65644,1.73926 -4.05828,2.73312292 Q 457.92231,0 455.10637,0 h -22.11345 q -3.3957,0 -3.3957,-3.4785201 0,-3.4785201 3.3957,-3.4785201 h 21.78216 q 2.6503,0 4.14109,-1.6564381 1.4908,-1.6564377 1.4908,-4.3895607 0,-5.549068 -5.63189,-5.549068 h -14.24537 q -2.73312,0 -4.96931,-0.828219 -2.2362,-0.911041 -3.89263,-2.484657 -1.57362,-1.656439 -2.48466,-3.89263 -0.91104,-2.236192 -0.91104,-4.886493 0,-2.650301 0.91104,-4.886492 0.91104,-2.236192 2.48466,-3.809808 1.65643,-1.656438 3.89263,-2.567479 2.23619,-0.911041 4.96931,-0.911041 z"
           style="stroke:#33663d;stroke-opacity:1"
           id="path1001"
           inkscape:connector-curvature="0" />
      </g>
    </g>
  </g>
</svg>    
    '''



