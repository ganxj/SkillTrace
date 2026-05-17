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
cd /d "%ROOT%\apps\mobile_flutter\android"
call gradlew.bat --no-daemon assembleDebug
cd /d "%ROOT%"
adb install -r "apps\mobile_flutter\build\app\outputs\flutter-apk\app-debug.apk"
adb shell monkey -p com.ailearningos.ai_learning_os_mobile -c android.intent.category.LAUNCHER 1

