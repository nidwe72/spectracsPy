from model.application.video.VideoSignal import VideoSignal


class ImageSpectrumAcquisitionLogicModuleParameters:

    __videoSignal: VideoSignal = None

    def getVideoSignal(self):
        return self.__videoSignal


    def setVideoSignal(self, videoSignal):
        self.__videoSignal = videoSignal
        return self

