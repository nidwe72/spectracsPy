from socket import socket, AF_INET, SOCK_STREAM, SOCK_DGRAM, AddressFamily

import psutil
from psutil._common import addr

from sciens.base.Singleton import Singleton


class NetworkUtil(Singleton):


    def getAddressUsingPort(self, port)->addr:

        result=None

        AD = "-"
        AF_INET6 = getattr(socket, 'AF_INET6', object())
        proto_map = {
            (AF_INET, SOCK_STREAM): 'tcp',
            (AF_INET6, SOCK_STREAM): 'tcp6',
            (AF_INET, SOCK_DGRAM): 'udp',
            (AF_INET6, SOCK_DGRAM): 'udp6',
        }

        templ = "%-5s %-30s %-30s %-13s %-6s %s"
        print(templ % (
            "Proto", "Local address", "Remote address", "Status", "PID",
            "Program name"))
        proc_names = {}
        for p in psutil.process_iter(['pid', 'name']):
            proc_names[p.info['pid']] = p.info['name']
        for c in psutil.net_connections(kind='inet'):

            if c.laddr.port==port:
                result = c.laddr
                break

            # laddr = "%s:%s" % (c.laddr)
            # raddr = ""
            # if c.raddr:
            #     raddr = "%s:%s" % (c.raddr)
            # name = proc_names.get(c.pid, '?') or ''
            # print(templ % (
            #     proto_map[(c.family, c.type)],
            #     laddr,
            #     raddr or AD,
            #     c.status,
            #     c.pid or AD,
            #     name[:15],
            # ))

        return result

    def getLocalIpAddress(self) -> str:
        result=None
        addressesByInterfaces = psutil.net_if_addrs()
        for interfaceName in addressesByInterfaces:
            if interfaceName.startswith('wlp') or interfaceName.startswith('eth0'):
                addresses=addressesByInterfaces.get(interfaceName)
                for someAddress in addresses:
                    family=someAddress.family
                    if family==AddressFamily.AF_INET:
                        result=someAddress.address
                        break
            if result is not None:
                break
        return result





