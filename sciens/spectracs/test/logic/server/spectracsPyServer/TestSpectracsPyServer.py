
import serpent
import Pyro5.api
import Pyro5.client
# from Pyro5.utils import getPyroTraceback

from sciens.spectracs.logic.model.util.SpectrometerUtil import SpectrometerUtil


class TestSpectracsPyServer:

    # def test_test(self):
    #     spectracsPyServer = Pyro5.Proxy('PYRO:sciens.SpectracsPyServer@localhost:41145')
    #     version = spectracsPyServer.getVersion()
    #     print(version)
    #     assert version is not None

    def test_test2(self):
        # nameserverUri: PYRO:Pyro.NameServer @ 192.168
        # .8
        # .111: 8090

        # Pyro5.config.SERIALIZER = "json"

        host = "192.168.8.111"
        port = 8090
        nameserver = Pyro5.api.locate_ns(host=host,port=port)
        uri = nameserver.lookup("sciens.spectracs.spectracsPyServer")

        spectracsPyServer = Pyro5.client.Proxy(uri)
        # persistentSpectrometers = spectracsPyServer.getPersistentSpectrometers()

        localSpectrometers = SpectrometerUtil().getSpectrometers()

        # to_dict = next(iter(localSpectrometers.values())).to_dict()

        try:
            # serialize = serpent.dumps(localSpectrometers)
            # tobytes = serpent.tobytes(localSpectrometers)



            spectracsPyServer.syncSpectrometers(localSpectrometers)
        except Exception:
            print('')
            # traceback = getPyroTraceback()
            # print(traceback)

        # print('=====persistentSpectrometers=====')
        # print(persistentSpectrometers)
        assert 1==1


