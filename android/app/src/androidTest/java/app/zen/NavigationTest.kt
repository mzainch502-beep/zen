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
class FixtureRepository(signedIn: Boolean=true,private val live: Boolean=false,private val losses:Boolean=false) : ZenRepository {
    override var base="https://instrumentation.invalid"
    override var token=if(signedIn) "instrumentation-only-session" else ""
    val calls=java.util.Collections.synchronizedList(mutableListOf<String>())
    private var mode=if(live) "Paused" else "Paper"
    private var automatic=false
    private var profile="balanced"
    private val learningWeights=if(losses) """{"momentum:trend":{"samples":5,"suspended":true},"pullback:expansion":{"samples":16,"suspended":true},"pullback:trend":{"samples":15,"suspended":true},"momentum:range":{"samples":7,"suspended":true},"range_reversion:range":{"samples":9,"suspended":true},"momentum:expansion":{"samples":6,"suspended":true},"range_reversion:expansion":{"samples":4,"weight":-0.2,"suspended":false},"pullback:range":{"samples":4,"weight":-0.1,"suspended":false}}""" else "{}"
    var profileBody: JSONObject? = null
    var futuresBody: JSONObject? = null
    override suspend fun call(path: String,method: String,body: JSONObject?): String {
        calls.add("$method $path")
        return when {
            path=="/auth/login" -> """{"token":"instrumentation-only-session"}"""
            path=="/futures/settings" -> {futuresBody=body;"""{"saved":true}"""}
            path=="/auth/logout" -> """{"revoked":true}"""
            path=="/agent/paper-profile" -> {profileBody=body;profile=body!!.getString("profile");automatic=true;"{}"}
            path=="/agent/automation" -> {automatic=body!!.getBoolean("enabled");"{}"}
            path=="/agent/mode" -> {mode=body!!.getString("mode");"""{"mode":"$mode"}"""}
            path=="/health" -> """{"status":"ok","worker_online":true,"live_execution":false}"""
            path=="/markets" -> """[{"stale":false,"quote":{"symbol":"BTC/USDT","last":"102425.25","bid":"102425.2","ask":"102425.3","change_percent":"0.4","source":"instrumentation-fixture"}},{"stale":false,"quote":{"symbol":"ETH/USDT","last":"3402.15","bid":"3402.1","ask":"3402.2","change_percent":"-0.7","source":"instrumentation-fixture"}}]"""
            path=="/snapshot" -> """{"research":{"profile":"$profile","catalogue_count":200,"recent_evaluations":12,"learning":{"weights":$learningWeights,"samples":${if(losses)66 else 0},"status":"collecting outcomes","version":"contextual-paper-v2"}},"automation":{"enabled":$automatic,"requested":$automatic,"can_enable":${!live},"product":"spot","blocked_reason":${if(live) "\"Live strategy validation pending\"" else "null"}},"account":{"email":"qa-owner@example.invalid"},"futures":{"activated":$live},"portfolio":{"paper":${!live},"mode":"$mode","equity":"200","cash":"200","daily_net":"0","net_pnl":"0","unrealized":"0","target":"25","exposure":"0","stale":false},"positions":[],"connections":[],"events":[],"agent":{"action":"WAIT","version":"research-v1","summary":"Observing market structure and execution conditions","reason":"Execution strategies remain gated by validation."},"limits":{"max_loss_trade":"2","max_daily_loss":"6","max_notional":"40","max_correlated_notional":"40","max_drawdown":"20","max_positions":2,"max_spread_bps":"20","max_slippage_bps":"10","max_order_rate":6,"cooldown_seconds":300,"max_leverage":"1","min_liquidation_buffer":"0.2"}}"""
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
        compose.onNodeWithText("The investment\noperating system.").assertExists();capture("welcome")
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
        compose.onNodeWithTag("nav-TRADE").performClick()
        compose.onNodeWithTag("nav-TRADE").assertIsSelected()
        compose.onNodeWithText("Search markets").assertExists();capture("markets")
        compose.onNodeWithTag("nav-AI").performClick()
        compose.onNodeWithText("Intelligence").assertExists();capture("agent")
        compose.onNodeWithText("Pause new positions").performScrollTo().performClick()
        compose.onNodeWithText("Pause",useUnmergedTree=true).performClick()
        compose.waitUntil(10000) {fixture.calls.contains("POST /agent/mode")}
        compose.onNodeWithTag("nav-PORTFOLIO").performClick()
        compose.onNodeWithTag("portfolio-scroll").performScrollToNode(hasText("No open positions"))
        compose.onNodeWithText("No open positions").assertExists();capture("positions")
        compose.onNodeWithTag("nav-MORE").performClick()
        compose.onNodeWithText("Workspace").assertExists();capture("settings")
        compose.onNodeWithTag("more-scroll").performScrollToNode(hasText("Settings"))
        compose.onNodeWithText("Settings").performClick()
        compose.onNodeWithTag("section-scroll").performScrollToNode(hasText("Risk limits"))
        compose.onNodeWithText("Risk limits").performClick()
        compose.onNodeWithText("Shared paper").performClick()
        compose.onNodeWithTag("field-Maximum trade loss · USDT").performScrollTo().assertExists();capture("risk")
    }
    @Test fun futuresControlsSendExplicitConfiguration() {
        val fixture=FixtureRepository()
        compose.setContent {ZenApp(repository=fixture)}
        compose.waitUntil(10000) {fixture.calls.contains("GET /snapshot")}
        compose.onNodeWithTag("nav-MORE").performClick()
        compose.onNodeWithTag("more-scroll").performScrollToNode(hasText("Settings"))
        compose.onNodeWithText("Settings").performClick()
        compose.onNodeWithTag("section-scroll").performScrollToNode(hasText("Trading controls"))
        compose.onNodeWithText("Trading controls").performClick()
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
    @Test fun aggressiveProfileIsExplicitAndSentToBackend() {
        val fixture=FixtureRepository()
        compose.setContent {ZenApp(repository=fixture)}
        compose.waitUntil(10000) {fixture.calls.contains("GET /snapshot")}
        compose.onNodeWithTag("nav-MORE").performClick()
        compose.onNodeWithTag("more-scroll").performScrollToNode(hasText("Strategies"))
        compose.onNodeWithText("Strategies").performClick()
        compose.onNodeWithTag("section-scroll").performScrollToNode(hasText("Aggressive"))
        compose.onNodeWithText("Aggressive").performClick()
        compose.onNodeWithText("Start paper").performClick()
        compose.waitUntil(10000) {fixture.calls.contains("POST /agent/paper-profile")}
        org.junit.Assert.assertEquals("aggressive",fixture.profileBody?.getString("profile"))
        compose.onNodeWithTag("automatic-trading-switch").assertIsOn()
        compose.onNodeWithTag("nav-AI").performClick()
        compose.onNodeWithTag("agent-scroll").performScrollToNode(hasText("Learning journal"))
        compose.onNodeWithText("Learning journal").assertIsDisplayed()
        capture("learning-desk")
    }
    @Test fun themeAndStockFilterAreFunctional() {
        val fixture=FixtureRepository()
        compose.setContent {ZenApp(repository=fixture)}
        compose.waitUntil(10000) {fixture.calls.contains("GET /snapshot")}
        compose.onNodeWithTag("nav-TRADE").performClick()
        compose.onNodeWithText("Stock-linked",useUnmergedTree=true).performClick()
        capture("stock-filter-empty")
        compose.onNodeWithTag("nav-MORE").performClick()
        compose.onNodeWithTag("more-scroll").performScrollToNode(hasText("Settings"))
        compose.onNodeWithText("Settings").performClick()
        compose.onNodeWithTag("theme-switch").performClick()
        capture("light-settings")
        compose.onNodeWithTag("nav-HOME").performClick()
        capture("light-home")
        compose.onNodeWithTag("nav-MORE").performClick()
        compose.onNodeWithTag("more-scroll").performScrollToNode(hasText("Settings"))
        compose.onNodeWithText("Settings").performClick()
        compose.onNodeWithTag("theme-switch").performClick()
    }

    @Test fun lossReviewRowsKeepAllGroupsReadable() {
        val fixture=FixtureRepository(losses=true)
        compose.setContent {ZenApp(repository=fixture)}
        compose.waitUntil(10000) {fixture.calls.contains("GET /snapshot")}
        compose.onNodeWithTag("nav-AI").performClick()
        compose.onNodeWithTag("agent-scroll").performScrollToNode(hasText("Learning journal"))
        compose.onNodeWithText("Momentum · expansion").performScrollTo()
        compose.onAllNodesWithText("Review required").assertCountEquals(6)
        compose.onNodeWithText("Momentum · trend").assertExists()
        compose.onNodeWithText("Pullback · range").assertExists()
        capture("learning-loss-review")
        compose.onNodeWithText("Range reversion · range").performScrollTo()
        compose.onNodeWithText("Range reversion · expansion").assertExists()
        capture("learning-all-groups")
    }
    @Test fun pausedLiveWorkspaceKeepsLiveLabel() {
        val fixture=FixtureRepository(live=true)
        compose.setContent {ZenApp(repository=fixture)}
        compose.waitUntil(10000) {fixture.calls.contains("GET /snapshot")}
        compose.onNodeWithText("LIVE · PAUSED").assertExists()
    }

}
