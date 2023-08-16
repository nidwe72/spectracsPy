

import Pyro4


class TestSpectracsPyServer:

    # def test_test(self):
    #     spectracsPyServer = Pyro4.Proxy('PYRO:sciens.SpectracsPyServer@localhost:41145')
    #     version = spectracsPyServer.getVersion()
    #     print(version)
    #     assert version is not None

    def test_test2(self):
        # nameserverUri: PYRO:Pyro.NameServer @ 192.168
        # .8
        # .111: 8090

        host = "192.168.8.111"
        port = 8090
        nameserver = Pyro4.locateNS(host=host,port=port)
        uri = nameserver.lookup("sciens.spectracs.spectracsPyServer")

        spectracsPyServer = Pyro4.Proxy(uri)
        persistentSpectrometers = spectracsPyServer.getPersistentSpectrometers()
        print('=====persistentSpectrometers=====')
        print(persistentSpectrometers)
        assert 1==1


