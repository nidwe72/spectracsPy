from model.databaseEntity.spectral.device.DbSpectralDevice import DbSpectralDevice
import typing

class SettingsLogicModule:

    def getSupportedSpectralDevices(self)->typing.Dict[str, DbSpectralDevice]:

        result={}

        microdiaDevice=DbSpectralDevice()
        microdiaDevice.name = "Microdia 0c45:6366"
        microdiaDevice.description = "Thunder optics"
        microdiaDevice.vendorId="0c45"
        microdiaDevice.modelId = "6366"
        result[microdiaDevice.name]=microdiaDevice

        sonixDevice=DbSpectralDevice()
        sonixDevice.name = "Sonix 0c45:6366"
        sonixDevice.description = "Waveshare"
        sonixDevice.vendorId="0c45"
        sonixDevice.modelId = "7777"
        result[sonixDevice.name]=sonixDevice


        return result

