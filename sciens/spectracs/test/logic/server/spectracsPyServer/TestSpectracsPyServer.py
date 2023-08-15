

import Pyro4


class TestSpectracsPyServer:

    # def test_test(self):
    #     spectracsPyServer = Pyro4.Proxy('PYRO:sciens.SpectracsPyServer@localhost:41145')
    #     version = spectracsPyServer.getVersion()
    #     print(version)
    #     assert version is not None

    def test_test2(self):
        spectracsPyServer = Pyro4.Proxy('PYRO:sciens.SpectracsPyServer@localhost:45395')
        persistentSpectrometers = spectracsPyServer.getPersistentSpectrometers()
        print('=====persistentSpectrometers=====')
        print(persistentSpectrometers)
        assert 1==1


