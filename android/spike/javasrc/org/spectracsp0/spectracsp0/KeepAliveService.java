package org.spectracsp0.spectracsp0;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.IBinder;

/**
 * P4g keep-alive — a minimal SAME-PROCESS foreground service (see docs/SPEC_android_port.md §3.2).
 *
 * The heavy main UI process (~217 MB: Qt + scipy + opencv) is otherwise reclaimed by Android while it
 * is backgrounded behind the native Storage-Access-Framework folder picker, so the picker result is
 * lost. Starting this foreground service right before launching the picker raises the process oom
 * priority so it survives; it is stopped as soon as the picker returns. It runs in the MAIN process
 * (no android:process in the manifest) — that is the whole point; a separate-process service would
 * not protect the UI process.
 */
public class KeepAliveService extends Service {
    private static final String CHANNEL_ID = "spectracs_keepalive";
    private static final int NOTIF_ID = 4711;

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        NotificationManager nm =
            (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            nm.createNotificationChannel(new NotificationChannel(
                CHANNEL_ID, "Spectracs", NotificationManager.IMPORTANCE_LOW));
        }
        Notification.Builder builder = (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            ? new Notification.Builder(this, CHANNEL_ID)
            : new Notification.Builder(this);
        Notification notification = builder
            .setContentTitle("Spectracs")
            .setContentText("Selecting folder…")
            .setSmallIcon(android.R.drawable.ic_menu_gallery)
            .setOngoing(true)
            .build();
        // API 34+ requires the foregroundServiceType (declared "shortService" in the manifest).
        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(NOTIF_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_SHORT_SERVICE);
        } else {
            startForeground(NOTIF_ID, notification);
        }
        return START_NOT_STICKY;  // don't relaunch if the process is killed anyway
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
