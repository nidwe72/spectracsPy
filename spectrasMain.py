import sys
import cv2
from PyQt6 import QtWidgets, QtCore,QtGui

from PyQt6.QtCore import QThread, Qt, pyqtSignal, pyqtSlot

from PyQt6.QtGui import QImage, QPixmap

from PyQt6.QtGui import QImage

from view.main.MainViewModule import MainViewModule


from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule

app = QtWidgets.QApplication(sys.argv)

mainViewModule=MainViewModule();
mainViewModule.resize(400, 200)
mainViewModule.setWindowTitle("Spectracs")

ApplicationContextLogicModule()

cap = cv2.VideoCapture(0)

ret, frame = cap.read()
if ret:
    rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    current_brightness = cap.get(cv2.CAP_PROP_BRIGHTNESS)
    print(current_brightness)

    gain = cap.get(cv2.CAP_PROP_GAIN)
    print(gain)
    #try another backend, CAP_DSHOW, CAP_MSMF, etc.

    h, w, ch = rgbImage.shape
    print(w)
    bytesPerLine = ch * w
    convertToQtFormat = QImage(rgbImage.data, w, h, bytesPerLine, QImage.Format.Format_Grayscale16)
    p = convertToQtFormat.scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio)
    width=p.width()
    print(width)




mainViewModule.show()



exit(app.exec())