[app]
title = UJAT Control Horarios
package.name = ujatcontrol
package.domain = org.ujat
source.dir = .
source.include_exts = py,kv,png,jpg,db
version = 1.0
requirements = python3,kivy==2.3.1,sqlite3
orientation = portrait
fullscreen = 0

android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
android.allow_aab = false
