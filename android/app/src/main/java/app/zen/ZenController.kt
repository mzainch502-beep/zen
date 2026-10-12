package app.zen

import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.runtime.mutableStateOf
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.json.JSONArray
import org.json.JSONObject

class ZenController(val repository: ZenRepository, private val scope: CoroutineScope) {
    var authorized by mutableStateOf(repository.token.isNotEmpty()); private set
    var loading by mutableStateOf(false); private set
    var connected by mutableStateOf(false); private set
    var error by mutableStateOf<String?>(null); private set
    var notice by mutableStateOf<String?>(null); private set
    var snapshot by mutableStateOf(JSONObject()); private set
    var markets by mutableStateOf(JSONArray()); private set
    var health by mutableStateOf(JSONObject()); private set
    var candles by mutableStateOf(JSONArray()); private set
    var depth by mutableStateOf(JSONObject()); private set
    var chartLoading by mutableStateOf(false); private set
    var chartError by mutableStateOf<String?>(null); private set
    var chartSymbol by mutableStateOf("BTC/USDT"); private set
    var chartTimeframe by mutableStateOf("5m"); private set
    private val commandLock = Mutex()
    private val refreshLock = Mutex()
    val portfolio get() = snapshot.optJSONObject("portfolio") ?: JSONObject()
    val positions get() = snapshot.optJSONArray("positions") ?: JSONArray()
    val events get() = snapshot.optJSONArray("events") ?: JSONArray()
    val limits get() = snapshot.optJSONObject("limits") ?: JSONObject()
    val connections get() = snapshot.optJSONArray("connections") ?: JSONArray()
    val agent get() = snapshot.optJSONObject("agent") ?: JSONObject()

    private fun failure(e: Exception) {
        error = e.message ?: "Connection failed. Please retry."
        connected = false
        if (e is ApiFailure && e.code == 401) { authorized = false; repository.clearSession(); snapshot = JSONObject(); markets = JSONArray() }
    }
    private suspend fun refreshData() = refreshLock.withLock {
        coroutineScope {
            val state = async { repository.call("/snapshot") }
            val prices = async { repository.call("/markets") }
            val status = async { repository.call("/health") }
            val newSnapshot = JSONObject(state.await())
            val newMarkets = JSONArray(prices.await())
            val newHealth = JSONObject(status.await())
            snapshot = newSnapshot; markets = newMarkets; health = newHealth; connected = true
        }
    }
    fun refresh() { scope.launch { try { refreshData(); error=null } catch(e: Exception) { failure(e) } } }
    suspend fun poll() {
        while (authorized) { try { refreshData(); error=null } catch(e: Exception) { failure(e) }; delay(8000) }
    }
    fun action(success: String? = null, work: suspend () -> Unit) {
        if (loading) return
        scope.launch { commandLock.withLock {
            loading = true; error = null; notice = null
            try { work(); if(success != null) notice=success } catch(e: Exception) { failure(e) } finally { loading=false }
        } }
    }
    fun login(email: String, password: String, server: String) = action {
        repository.base=server.trim()
        val result=JSONObject(repository.call("/auth/login","POST",JSONObject().put("email",email.trim()).put("password",password)))
        repository.token=result.getString("token"); authorized=true; refreshData()
    }
    fun setup(email: String,password: String,invite: String,server: String) = action("Account created. Your paper workspace is ready.") {
        repository.base=server.trim()
        repository.call("/auth/setup","POST",JSONObject().put("email",email.trim()).put("password",password).put("setup_token",invite.trim()))
        val result=JSONObject(repository.call("/auth/login","POST",JSONObject().put("email",email.trim()).put("password",password)))
        repository.token=result.getString("token");authorized=true;refreshData()
    }
    fun mode(value: String) = action(when(value) {"Paper"->"Paper workspace resumed.";"Paused"->"New positions paused. Existing exits remain active.";else->"Emergency stop active. No new positions can open."}) {
        repository.call("/agent/mode","POST",JSONObject().put("mode",value));refreshData()
    }
    fun saveRisk(body: JSONObject) = action("Risk limits saved.") { repository.call("/risk","PUT",body);refreshData() }
    fun order(body: JSONObject) = action("Paper order completed. No exchange order was sent.") { repository.call("/paper/orders","POST",body);refreshData() }
    fun exits(id: String,stop: String,take: String) = action("Protective exits updated.") {
        repository.call("/positions/$id/exits","PUT",JSONObject().put("stop",stop).put("take_profit",if(take.isBlank()) JSONObject.NULL else take));refreshData()
    }
    fun connect(exchange: String,key: String,secret: String,passphrase: String,done: ()->Unit) = action("Connection tested and saved securely.") {
        repository.call("/connections","POST",JSONObject().put("exchange",exchange).put("api_key",key.trim()).put("secret",secret.trim()).put("passphrase",if(passphrase.isBlank()) JSONObject.NULL else passphrase).put("read_only_attestation",true));done();refreshData()
    }
    fun removeConnection(id: String) = action("Saved credentials removed. Revoke the key on your exchange too.") {repository.call("/connections/$id","DELETE");refreshData()}
    fun export(share: (String)->Unit) = action { share(repository.call("/audit/export")) }
    fun logout() = action {
        try { repository.call("/auth/logout","POST") } finally { repository.clearSession();authorized=false;connected=false;snapshot=JSONObject();markets=JSONArray() }
    }
    fun clearNotice() { notice=null }
    fun clearError() { error=null }
    fun chart(symbol: String,tf: String) {
        chartSymbol=symbol;chartTimeframe=tf;chartLoading=true;chartError=null; candles=JSONArray();depth=JSONObject()
        scope.launch {
            try {
                val encoded=java.net.URLEncoder.encode(symbol,"UTF-8")
                val value=JSONObject(repository.call("/candles?symbol=$encoded&timeframe=$tf"))
                if(chartSymbol==symbol && chartTimeframe==tf) candles=value.getJSONArray("candles")
                val orderBook=JSONObject(repository.call("/market-depth?symbol=$encoded"))
                if(chartSymbol==symbol && chartTimeframe==tf) depth=orderBook
            } catch(e: Exception) { if(chartSymbol==symbol && chartTimeframe==tf) chartError=e.message }
            finally { if(chartSymbol==symbol && chartTimeframe==tf) chartLoading=false }
        }
    }
}
fun JSONObject.value(key: String): String? = if(!has(key) || isNull(key)) null else optString(key).takeIf { it.isNotBlank() }
fun JSONArray.rows(): List<JSONObject> = (0 until length()).map { getJSONObject(it) }
