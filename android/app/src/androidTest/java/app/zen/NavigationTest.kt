package app.zen

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.*
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Rule
import org.junit.Test
import org.json.JSONObject
import java.io.File
import android.graphics.Bitmap

/** Synthetic responses exist only in the instrumentation APK, never in the production app. */
class FixtureRepository(signedIn: Boolean=true,private val live: Boolean=false) : ZenRepository {
    override var base="https://instrumentation.invalid"
    override var token=if(signedIn) "instrumentation-only-session" else ""
    val calls=java.util.Collections.synchronizedList(mutableListOf<String>())
    private var mode=if(live) "Paused" else "Paper"
    private var automatic=false
    var futuresBody: JSONObject? = null
    override suspend fun call(path: String,method: String,body: JSONObject?): String {
        calls.add("$method $path")
        return when {
            path=="/auth/login" -> """{"token":"instrumentation-only-session"}"""
            path=="/futures/settings" -> {futuresBody=body;"""{"saved":true}"""}
            path=="/auth/logout" -> """{"revoked":true}"""
            path=="/agent/automation" -> {automatic=body!!.getBoolean("enabled");"{}"}
            path=="/agent/mode" -> {mode=body!!.getString("mode");"""{"mode":"$mode"}"""}
            path=="/health" -> """{"status":"ok","worker_online":true,"live_execution":false}"""
            path=="/markets" -> """[{"stale":false,"quote":{"symbol":"BTC/USDT","last":"102425.25","bid":"102425.2","ask":"102425.3","change_percent":"0.4","source":"instrumentation-fixture"}},{"stale":false,"quote":{"symbol":"ETH/USDT","last":"3402.15","bid":"3402.1","ask":"3402.2","change_percent":"-0.7","source":"instrumentation-fixture"}}]"""
            path=="/snapshot" -> """{"automation":{"enabled":$automatic,"requested":$automatic,"can_enable":${!live},"product":"spot","blocked_reason":${if(live) "\"Live strategy validation pending\"" else "null"}},"account":{"email":"qa-owner@example.invalid"},"futures":{"activated":$live},"portfolio":{"paper":${!live},"mode":"$mode","equity":"200","cash":"200","daily_net":"0","net_pnl":"0","unrealized":"0","target":"25","exposure":"0","stale":false},"positions":[],"connections":[],"events":[],"agent":{"action":"WAIT","version":"research-v1","summary":"Observing market structure and execution conditions","reason":"Execution strategies remain gated by validation."},"limits":{"max_loss_trade":"2","max_daily_loss":"6","max_notional":"40","max_correlated_notional":"40","max_drawdown":"20","max_positions":2,"max_spread_bps":"20","max_slippage_bps":"10","max_order_rate":6,"cooldown_seconds":300,"max_leverage":"1","min_liquidation_buffer":"0.2"}}"""
            path.startsWith("/candles") -> """{"candles":[[1700000000000,100,102,99,101,1000],[1700000300000,101,103,100,102,1200]]}"""
            path.startsWith("/market-depth") -> """{"source":"instrumentation-fixture","bids":[[100,1]],"asks":[[101,1]]}"""
            path=="/audit/export" -> "[]"
            else -> "{}"
        }
    }
}
class NavigationTest {
    @get:Rule val compose=createComposeRule()
    private fun capture(name: String) {
        val instrumentation=InstrumentationRegistry.getInstrumentation()
        // Only synthetic instrumentation screens are captured; production keeps FLAG_SECURE.
        instrumentation.runOnMainSync {
            androidx.test.runner.lifecycle.ActivityLifecycleMonitorRegistry.getInstance()
                .getActivitiesInStage(androidx.test.runner.lifecycle.Stage.RESUMED)
                .forEach {it.window.clearFlags(android.view.WindowManager.LayoutParams.FLAG_SECURE)}
        }
        compose.waitForIdle()
        val directory=instrumentation.uiAutomation.executeShellCommand("mkdir -p /sdcard/Download/zen-ui-qa")
        android.os.ParcelFileDescriptor.AutoCloseInputStream(directory).use {it.readBytes()}
        val descriptor=instrumentation.uiAutomation.executeShellCommand("screencap -p /sdcard/Download/zen-ui-qa/$name.png")
        android.os.ParcelFileDescriptor.AutoCloseInputStream(descriptor).use {it.readBytes()}
    }
    @Test fun signInInputsAndConnectionSettingsWork() {
        val fixture=FixtureRepository(false)
        compose.setContent {ZenApp(repository=fixture)}
        compose.onNodeWithText("Welcome back").assertExists();capture("welcome")
        compose.onNodeWithTag("field-Owner email").performScrollTo().performTextInput("qa-owner@example.invalid")
        compose.onNodeWithTag("password-input").performScrollTo().performTextInput("instrumentation-password")
        compose.onNode(hasText("Sign in") and hasClickAction()).performScrollTo().performClick()
        compose.waitUntil(10000) {fixture.calls.contains("GET /snapshot")}
        compose.onNodeWithText("Overview").assertExists()
        assert(fixture.calls.contains("POST /auth/login"))
    }
    @Test fun fiveTabsRiskAndAgentControlsUseRepository() {
        val fixture=FixtureRepository()
        compose.setContent {ZenApp(repository=fixture)}
        compose.waitUntil(10000) {fixture.calls.contains("GET /markets")}
        compose.onNodeWithText("Overview").assertExists();capture("home")
        compose.onNodeWithTag("nav-MARKETS").performClick()
        compose.onNodeWithText("Search markets").assertExists();capture("markets")
        compose.onNodeWithTag("nav-AGENT").performClick()
        compose.onNodeWithText("Intelligence").assertExists();capture("agent")
        compose.onNodeWithText("Pause new positions").performScrollTo().performClick()
        compose.onNodeWithText("Pause",useUnmergedTree=true).performClick()
        compose.waitUntil(10000) {fixture.calls.contains("POST /agent/mode")}
        compose.onNodeWithTag("nav-POSITIONS").performClick()
        compose.onNodeWithText("No open positions").assertExists();capture("positions")
        compose.onNodeWithTag("nav-SETTINGS").performClick()
        compose.onNodeWithText("Workspace").assertExists();capture("settings")
        compose.onNodeWithText("Risk limits").performScrollTo().performClick()
        compose.onNodeWithText("Loss per trade · USDT").assertExists();capture("risk")
    }
    @Test fun futuresControlsSendExplicitConfiguration() {
        val fixture=FixtureRepository()
        compose.setContent {ZenApp(repository=fixture)}
        compose.waitUntil(10000) {fixture.calls.contains("GET /snapshot")}
        compose.onNodeWithTag("nav-SETTINGS").performClick()
        compose.onNodeWithText("Trading controls").performScrollTo().performClick()
        compose.onNodeWithText("Perpetual futures").performClick()
        compose.onNodeWithTag("field-Leverage ceiling · ×").performScrollTo().performTextClearance()
        compose.onNodeWithTag("field-Leverage ceiling · ×").performTextInput("10")
        capture("futures-controls")
        compose.onNodeWithText("Save trading controls").performScrollTo().performClick()
        compose.waitUntil(10000) {fixture.calls.contains("PUT /futures/settings")}
        org.junit.Assert.assertEquals("futures",fixture.futuresBody?.getString("workspace"))
        org.junit.Assert.assertEquals(10,fixture.futuresBody?.getJSONObject("limits")?.getInt("max_leverage"))
    }

    @Test fun automaticTradingSwitchWritesAndReflectsServerState() {
        val fixture=FixtureRepository()
        compose.setContent {ZenApp(repository=fixture)}
        compose.waitUntil(10000) {fixture.calls.contains("GET /snapshot")}
        compose.onNodeWithTag("automatic-trading-switch").assertIsOff().performClick()
        compose.onNodeWithText("Enable").performClick()
        compose.waitUntil(10000) {fixture.calls.contains("PUT /agent/automation")}
        compose.onNodeWithTag("automatic-trading-switch").assertIsOn()
        capture("automation-on")
        compose.onNodeWithTag("automatic-trading-switch").performClick()
        compose.waitUntil(10000) {fixture.calls.count {it=="PUT /agent/automation"}==2}
        compose.onNodeWithTag("automatic-trading-switch").assertIsOff()
    }
    @Test fun pausedLiveWorkspaceKeepsLiveLabel() {
        val fixture=FixtureRepository(live=true)
        compose.setContent {ZenApp(repository=fixture)}
        compose.waitUntil(10000) {fixture.calls.contains("GET /snapshot")}
        compose.onNodeWithText("LIVE · PAUSED").assertExists()
    }

}
