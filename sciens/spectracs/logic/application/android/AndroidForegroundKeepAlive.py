"""P4g — start/stop the same-process foreground keep-alive service around the native SAF folder
picker, so Android doesn't reclaim the heavy main app while it's backgrounded behind the picker.

Android-only; every call is a no-op on desktop and swallows JNI errors so a failure here can never
break the (desktop) picker flow. See docs/SPEC_android_port.md §3.2 and KeepAliveService.java.
"""
from sciens.base.PlatformUtil import is_android

_SERVICE_CLASS = "org.spectracsp0.spectracsp0.KeepAliveService"


def _activityAndIntent():
    from jnius import autoclass
    activity = autoclass("org.kivy.android.PythonActivity").mActivity
    intent = autoclass("android.content.Intent")(activity, autoclass(_SERVICE_CLASS))
    return activity, intent


def start():
    """Raise the main process's priority (foreground service) before launching the picker."""
    if not is_android():
        return
    try:
        activity, intent = _activityAndIntent()
        activity.startForegroundService(intent)
        print("keepalive: foreground service started")
    except Exception as error:  # pragma: no cover - device only
        print("keepalive: start failed: %r" % error)


def stop():
    """Drop the keep-alive as soon as the picker has returned."""
    if not is_android():
        return
    try:
        activity, intent = _activityAndIntent()
        activity.stopService(intent)
        print("keepalive: foreground service stopped")
    except Exception as error:  # pragma: no cover - device only
        print("keepalive: stop failed: %r" % error)
