import os
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QGroupBox
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QWidget

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from logic.spectral.video.SpectrumVideoThread import SpectrumVideoThread
from model.application.navigation.NavigationSignal import NavigationSignal
from model.databaseEntity.DbBase import session_factory
from model.databaseEntity.spectral.device.DbSpectralDevice import DbSpectralDevice
from model.spectral.SpectrumSampleType import SpectrumSampleType
from view.spectral.spectralJob.widget.SpectralJobWidgetViewModule import SpectralJobWidgetViewModule
from view.spectral.spectralJob.widget.SpectralJobWidgetViewModuleParameters import SpectralJobWidgetViewModuleParameters
from view.spectral.spectralJob.widget.SpectralJobsWidgetViewModule import SpectralJobsWidgetViewModule

from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import Session

from sqlalchemy.orm import sessionmaker

from sqlalchemy.orm import registry
from sqlalchemy import MetaData

class SpectralJobViewModule(QWidget):
    videoThread: SpectrumVideoThread

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()
        self.setLayout(layout)

        self.spectralJobsWidgetViewModule = SpectralJobsWidgetViewModule(self)
        layout.addWidget(self.spectralJobsWidgetViewModule, 0, 0, 1, 1)

        sampleButtonsGroupBox = self.createSampleButtonsGroupBox()
        layout.addWidget(sampleButtonsGroupBox, 1, 0, 1, 1)

        lightGroupBox = self.createLightButtonsGroupBox()
        layout.addWidget(lightGroupBox, 2, 0, 1, 1)

        navigationGroupBox = self.createNavigationGroupBox()
        layout.addWidget(navigationGroupBox, 3, 0, 1, 1)



    def createSampleButtonsGroupBox(self):
        lightGroupBox = QGroupBox("Oil")

        lightGroupBoxLayout = QGridLayout()
        lightGroupBox.setLayout(lightGroupBoxLayout);

        measureLightButton = QPushButton()
        measureLightButton.setText("Measure")
        lightGroupBoxLayout.addWidget(measureLightButton, 0, 0, 1, 1)

        importLightButton = QPushButton()
        importLightButton.setText("Import")
        lightGroupBoxLayout.addWidget(importLightButton, 0, 1, 1, 1)

        return lightGroupBox

    def createNavigationGroupBox(self):
        result = QGroupBox("")

        layout = QGridLayout()
        result.setLayout(layout);

        measureLightButton = QPushButton()
        measureLightButton.setText("Save")
        layout.addWidget(measureLightButton, 0, 0, 1, 1)

        importLightButton = QPushButton()
        importLightButton.setText("Back")
        layout.addWidget(importLightButton, 0, 1, 1, 1)
        importLightButton.clicked.connect(self.onClickedBackButton)

        return result

    def createLightButtonsGroupBox(self):
        lightGroupBox = QGroupBox("Light")

        lightGroupBoxLayout = QGridLayout()
        lightGroupBox.setLayout(lightGroupBoxLayout);

        measureLightButton = QPushButton()
        measureLightButton.setText("Measure")
        lightGroupBoxLayout.addWidget(measureLightButton, 0, 0, 1, 1)

        usePreviousLightMeasurementButton = QPushButton()
        usePreviousLightMeasurementButton.setText("Previous measurement")
        lightGroupBoxLayout.addWidget(usePreviousLightMeasurementButton, 0, 1, 1, 1)

        importLightButton = QPushButton()
        importLightButton.setText("Import")
        lightGroupBoxLayout.addWidget(importLightButton, 0, 2, 1, 1)

        measureLightButton.clicked.connect(self.onClickedMeasureLightButton)

        return lightGroupBox

    def onClickedMeasureLightButton(self):
        self.spectralJobsWidgetViewModule.referenceWidget.startVideoThread()
        self.foo()

    def onClickedImportButtonButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectralJobImport")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def onClickedBackButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("Home")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def foo(self):
        #todo:continue should have some LogicModule for actually persisting entities
        session=session_factory()

        DATABASE_DIR = os.path.dirname(os.path.abspath(__file__)) + '\\test.db'
        # engine = create_engine('sqlite:///' + DATABASE_DIR, echo=True)
        # engine = create_engine('sqlite:///./test.db')
        # spectralDevice = DbSpectralDevice()

        # mapper_registry = registry()
        # metadata_obj=mapper_registry.metadata

        # metadata_obj=MetaData()
        # metadata_obj.create_all(bind=engine)
        #
        # metadata_obj.create_all()
        #
        # session=sessionmaker()
        # session.configure(bind=engine)
        #
        # # session=Session(engine)
        # so=session.object_session()
        # session.ad

        spectralDevice = DbSpectralDevice()
        spectralDevice.horizontalDigitalResolution=1024
        spectralDevice.verticalDigitalResolution = 768
        session.add(spectralDevice)

        session.commit()


        #session.flush()


        pass


