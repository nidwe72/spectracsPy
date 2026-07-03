[app]
title = spectracsp0
package.name = spectracsp0
package.domain = org.spectracsp0
source.dir = ./app_src
source.include_exts = py,png,jpg,svg,ttf,qml,js,kv,atlas
version = 0.1
requirements = python3,shiboken6,PySide6,numpy,scipy,opencv,pyqtgraph,Pyro5,SQLAlchemy,sqlalchemy-serializer,marshmallow,marshmallow-sqlalchemy,colour-science,spectres,pillow,typing_extensions,colorama,networkx,imageio,serpent,libbz2,liblzma
orientation = portrait
osx.python_version = 3
osx.kivy_version = 1.9.1
fullscreen = 0
android.archs = arm64-v8a
android.minapi = 26
android.api = 34
android.allow_backup = True
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
ios.ios_deploy_branch = 1.10.0
ios.codesign.allowed = false
android.ndk_path = /home/nidwe72/.buildozer/android/platform/android-ndk-r28c
p4a.bootstrap = qt
p4a.local_recipes = /home/nidwe72/development/spectracs/spectracsPy/android/spike/deployment/recipes
p4a.branch = develop
android.permissions = android.permission.INTERNET, android.permission.WRITE_EXTERNAL_STORAGE
android.add_jars = /home/nidwe72/development/spectracs/spectracsPy/android/spike/deployment/jar/PySide6/jar/Qt6AndroidBindings.jar,/home/nidwe72/development/spectracs/spectracsPy/android/spike/deployment/jar/PySide6/jar/Qt6Android.jar
p4a.extra_args = --qt-libs=Gui,Widgets,Core --load-local-libs=plugins_platforms_qtforandroid --init-classes=
icon.filename = /home/nidwe72/development/spectracs/spectracsPy/android/tooling-venv/lib/python3.10/site-packages/PySide6/scripts/deploy_lib/pyside_icon.jpg

[buildozer]
log_level = 2
warn_on_root = 1
bin_dir = /home/nidwe72/development/spectracs/spectracsPy/android/spike

