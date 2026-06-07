package com.ailearningos.ai_learning_os_mobile

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val channelName = "ai_learning_os/current_course"
    private val prefsName = "ai_learning_os_mobile"
    private val currentDomainKey = "current_domain_id"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName).setMethodCallHandler { call, result ->
            val prefs = getSharedPreferences(prefsName, MODE_PRIVATE)
            when (call.method) {
                "getCurrentDomainId" -> result.success(prefs.getString(currentDomainKey, null))
                "setCurrentDomainId" -> {
                    val domainId = call.arguments as? String
                    if (domainId.isNullOrBlank()) {
                        result.error("invalid_domain_id", "domainId is required", null)
                    } else {
                        prefs.edit().putString(currentDomainKey, domainId).apply()
                        result.success(null)
                    }
                }
                else -> result.notImplemented()
            }
        }
    }
}
