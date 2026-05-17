@echo off
setlocal
set "ROOT=%~dp0.."
set "FLUTTER_STORAGE_BASE_URL=https://storage.flutter-io.cn"
set "PUB_HOSTED_URL=https://pub.dev"
set "PUB_CACHE=%ROOT%\.tools\pub-cache"
set "APPDATA=%ROOT%\.tools\appdata"
set "LOCALAPPDATA=%ROOT%\.tools\localappdata"
set "ANDROID_HOME=%ROOT%\.tools\android-sdk"
set "ANDROID_SDK_ROOT=%ROOT%\.tools\android-sdk"
set "JAVA_HOME=D:\Program Files\Android\Android Studio\jbr"
set "GRADLE_USER_HOME=%ROOT%\.tools\gradle"
set "PATH=%JAVA_HOME%\bin;%ANDROID_HOME%\platform-tools;%PATH%"
cd /d "%ROOT%"
adb reverse tcp:8000 tcp:8000
cd /d "%ROOT%\apps\mobile_flutter"
"%ROOT%\.tools\flutter\bin\flutter.bat" run -d 4f97fe05 --debug

