"""Entry point for the SERVER AppImage — docs/SPEC_linux_appimage.md §19.

Two entries, dispatched on argv, because they cannot be merged (§8f.1):

  no arguments  -> SpectracsPyServer.serveLocalForever(): a plain daemon on 127.0.0.1:8091 with the
                   fixed object id the client probes FIRST. No nameserver, no interface, no network.
  any argument  -> spectracsPyServer.main(): the stock CLI, sys.argv forwarded verbatim
                   (--local, --nameserverHost/Port, --daemonHost/Port, --daemonNatHost/Port, ...).

⛔ The stock CLI CANNOT serve on loopback: Pyro5.api.start_ns() returns broadcastServer=None when it
binds a loopback address, and spectracsPyServer.main() puts that None straight into select.select()
(:91-94) -> TypeError. That is why the no-argument default is a different entry, not a set of flags.
"""
import sys


def main():
    if len(sys.argv) > 1:
        import spectracsPyServer                      # top-level module of the -server repo
        spectracsPyServer.main()                      # argparse reads sys.argv itself
        return
    from sciens.spectracs.SpectracsPyServer import SpectracsPyServer
    SpectracsPyServer.serveLocalForever()             # blocking


if __name__ == "__main__":
    main()
