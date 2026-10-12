package app.zen
import android.os.Bundle
import android.content.Intent
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

val Ink = Color(0xFF080D12)
val Emerald = Color(0xFF44D7AA)
val Loss = Color(0xFFEB8691)
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE)
        setContent { ZenApp { text -> startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply { type="text/plain"; putExtra(Intent.EXTRA_TEXT,text) },"Export ZEN audit")) } }
    }
}
@Composable fun Pane(title: String, content: @Composable ColumnScope.() -> Unit) {
    Card(Modifier.fillMaxWidth(), colors=CardDefaults.cardColors(containerColor=Color(0xFF121C26))) {
        Column(Modifier.padding(18.dp), verticalArrangement=Arrangement.spacedBy(10.dp)) {
            Text(title, style=MaterialTheme.typography.titleMedium, fontWeight=FontWeight.SemiBold); content()
        }
    }
}
@Composable fun Metric(label: String, value: String) { Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) { Text(label,color=Color(0xFFA5B7C8));Text(value,fontWeight=FontWeight.Medium) } }
fun JSONObject.display(key: String) = if (isNull(key) || !has(key)) "Unavailable" else get(key).toString()
fun JSONArray.objects(): List<JSONObject> = (0 until length()).map { getJSONObject(it) }
@Composable fun ZenApp(share: (String)->Unit = {}) {
    MaterialTheme(colorScheme=darkColorScheme(primary=Emerald,background=Ink,surface=Ink,error=Loss)) {
        val api=remember { Api() }; val scope=rememberCoroutineScope()
        var logged by remember { mutableStateOf(false) };var url by remember { mutableStateOf("") }
        var setupToken by remember { mutableStateOf("") };var setupAccount by remember { mutableStateOf(false) }
        var email by remember { mutableStateOf("") };var password by remember { mutableStateOf("") }
        var page by remember { mutableStateOf("Home") };var error by remember { mutableStateOf<String?>(null) }
        var busy by remember { mutableStateOf(false) };var snapshot by remember { mutableStateOf(JSONObject()) }
        var markets by remember { mutableStateOf(JSONArray()) };var health by remember { mutableStateOf(JSONObject()) }
        var confirm by remember { mutableStateOf<Pair<String,()->Unit>?>(null) }
        var selectedPosition by remember { mutableStateOf<JSONObject?>(null) }
        var stop by remember { mutableStateOf("") };var tp by remember { mutableStateOf("") }
        var search by remember { mutableStateOf("") };var selectedSymbol by remember { mutableStateOf("BTC/USDT") }
        var timeframe by remember { mutableStateOf("1m") };var candles by remember { mutableStateOf(JSONArray()) }
        var favorites by remember { mutableStateOf(setOf<String>()) }
        var exchange by remember { mutableStateOf("binance") };var apiKey by remember { mutableStateOf("") }
        var secret by remember { mutableStateOf("") };var passphrase by remember { mutableStateOf("") };var readOnly by remember { mutableStateOf(false) }
        var riskDaily by remember { mutableStateOf("6") };var riskTrade by remember { mutableStateOf("2") };var riskExposure by remember { mutableStateOf("40") }
        var riskLoaded by remember { mutableStateOf(false) }
        var qty by remember { mutableStateOf("") };var orderStop by remember { mutableStateOf("") }
        suspend fun refresh() { snapshot=JSONObject(api.call("/snapshot")); markets=JSONArray(api.call("/markets"));health=JSONObject(api.call("/health")); if(!riskLoaded) { val lim=snapshot.getJSONObject("limits");riskDaily=lim.getString("max_daily_loss");riskTrade=lim.getString("max_loss_trade");riskExposure=lim.getString("max_notional");riskLoaded=true } }
        fun task(work: suspend ()->Unit) { if (busy) return;scope.launch { busy=true;error=null;try { work() } catch(e: Exception) { error=e.message ?: "Connection failed";if(api.token.isEmpty()) logged=false } finally { busy=false } } }
        fun mode(value: String) = task { api.call("/agent/mode","POST",JSONObject().put("mode",value)); refresh() }
        fun reduce(p: JSONObject,fraction: String) {
            val quantity=p.getString("quantity").toBigDecimal()*fraction.toBigDecimal()
            task { api.call("/paper/orders","POST",JSONObject().put("symbol",p.getString("symbol")).put("side","sell").put("quantity",quantity.toPlainString()).put("reduce_only",true).put("idempotency_key",UUID.randomUUID().toString()));refresh() }
        }
        LaunchedEffect(logged) {
            while(logged) { delay(5000); if(!busy) { try { refresh();error=null } catch(e: Exception) { error=e.message;if(api.token.isEmpty()) logged=false } } }
        }
        val p=snapshot.optJSONObject("portfolio") ?: JSONObject()
        Scaffold(containerColor=Ink,bottomBar={ if(logged) NavigationBar(containerColor=Ink) {
            listOf("Home","Markets","Agent","Positions","Settings").forEachIndexed { i,label ->
                NavigationBarItem(selected=page==label,onClick={page=label},icon={Text(listOf("◉","▥","◎","▤","⚙")[i])},label={Text(label)})
            }
        } }) { padding ->
            Column(Modifier.padding(padding).padding(horizontal=20.dp).fillMaxSize().verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(14.dp)) {
                Spacer(Modifier.height(10.dp))
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                    Text("ZEN",style=MaterialTheme.typography.headlineLarge,fontWeight=FontWeight.Bold,color=Emerald)
                    Text(if(logged) "${p.display("mode")} • SPOT" else "OFFLINE",modifier=Modifier.padding(top=12.dp),color=Color(0xFF85B8ED))
                }
                Text(if(logged) "Your capital. Clear decisions." else "Connect to your private intelligence backend.",color=Color(0xFFA5B7C8))
                if(busy) LinearProgressIndicator(Modifier.fillMaxWidth())
                error?.let { Pane("Connection / action status") { Text(it,color=Loss);Text("Data may be stale. No success is assumed.");Button(onClick={task {refresh()}},enabled=logged && !busy){Text("Retry")}} }
                if(!logged) {
                    Pane("Secure sign in") {
                        OutlinedTextField(url,{url=it},label={Text("HTTPS backend URL")},singleLine=true,modifier=Modifier.fillMaxWidth())
                        OutlinedTextField(email,{email=it},label={Text("Owner email")},singleLine=true,modifier=Modifier.fillMaxWidth())
                        OutlinedTextField(password,{password=it},label={Text("Password")},visualTransformation=PasswordVisualTransformation(),singleLine=true,modifier=Modifier.fillMaxWidth())
                        Button(onClick={task { api.base=url.trim();val result=JSONObject(api.call("/auth/login","POST",JSONObject().put("email",email).put("password",password)));api.token=result.getString("token");password="";refresh();logged=true }},enabled=!busy,modifier=Modifier.fillMaxWidth()){Text("Connect securely")}
                        TextButton(onClick={setupAccount=!setupAccount}){Text(if(setupAccount) "Hide first-time setup" else "Create owner account")}
                        if(setupAccount) {
                            OutlinedTextField(setupToken,{setupToken=it},label={Text("Owner setup token")},visualTransformation=PasswordVisualTransformation(),modifier=Modifier.fillMaxWidth())
                            Button(onClick={task {api.base=url.trim();api.call("/auth/setup","POST",JSONObject().put("email",email).put("password",password).put("setup_token",setupToken));setupToken="";setupAccount=false;error="Owner created. Remove setup token from hosting settings, then sign in."}},enabled=!busy){Text("Create securely")}
                        }
                        Text("Accounts are provisioned by the owner. Sessions stay in memory. Paper balances are simulated.",style=MaterialTheme.typography.bodySmall)
                    }
                } else when(page) {
                    "Home" -> {
                        Pane("Paper portfolio • USDT equivalent") {
                            Text(p.display("equity"),style=MaterialTheme.typography.displaySmall,fontWeight=FontWeight.Bold)
                            Metric("Available cash",p.display("cash"));Metric("Daily net P&L",p.display("daily_net"));Metric("Unrealized P&L",p.display("unrealized"));Metric("Net P&L",p.display("net_pnl"));Metric("Fees",p.display("fees"));Metric("Funding (spot)",p.display("funding"))
                            Text("$25/day aspirational target • never a trading quota",color=Color(0xFF85B8ED))
                            Metric("Exposure used",p.display("exposure"));Metric("Worker",if(health.optBoolean("worker_online")) "Online" else "Offline")
                            if(p.optBoolean("stale")) Text("Marks are stale; equity is unavailable",color=Loss)
                        }
                        Row(horizontalArrangement=Arrangement.spacedBy(10.dp)) {
                            Button(onClick={page="Positions"}){Text("Positions")};OutlinedButton(onClick={page="Settings"}){Text("Risk controls")}
                        }
                        Button(onClick={confirm="Stop all new exposure? Existing positions stay open until you close them." to {mode("Emergency Stop")}},enabled=!busy,colors=ButtonDefaults.buttonColors(containerColor=Loss),modifier=Modifier.fillMaxWidth()){Text("Emergency stop")}
                    }
                    "Markets" -> {
                        OutlinedTextField(search,{search=it},label={Text("Search BTC, ETH, SOL")},modifier=Modifier.fillMaxWidth())
                        if(markets.length()==0) Pane("No market data") { Text("Observer has not received real quotes. No prices are fabricated.") }
                        markets.objects().filter { it.getJSONObject("quote").getString("symbol").contains(search,true) }.forEach { m ->
                            val q=m.getJSONObject("quote");val symbol=q.getString("symbol")
                            Pane(symbol) {
                                Metric("Last",q.display("last"));Metric("Bid / Ask","${q.display("bid")} / ${q.display("ask")}");Metric("Change %",q.display("change_percent"));Metric("Source",q.display("source"))
                                Text(if(m.optBoolean("stale")) "STALE" else "Recent observation",color=if(m.optBoolean("stale")) Loss else Emerald)
                                Row { TextButton(onClick={selectedSymbol=symbol;task {candles=JSONObject(api.call("/candles?symbol=${symbol.replace("/","%2F")}&timeframe=$timeframe")).getJSONArray("candles")}}){Text("Chart")};TextButton(onClick={favorites=if(symbol in favorites) favorites-symbol else favorites+symbol}){Text(if(symbol in favorites) "Unfavorite" else "Favorite")} }
                            }
                        }
                        Pane("$selectedSymbol • $timeframe") {
                            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) { listOf("1m","5m","15m","1h","4h").forEach { tf -> TextButton(onClick={timeframe=tf;task {candles=JSONObject(api.call("/candles?symbol=${selectedSymbol.replace("/","%2F")}&timeframe=$tf")).getJSONArray("candles")}}){Text(tf)} } }
                            CandleChart(candles)
                            Text("Historical exchange candles. Funding and liquidation are not applicable to spot.",style=MaterialTheme.typography.bodySmall)
                        }
                        Pane("Paper test order") {
                            Text("$selectedSymbol • simulated spot LONG only. All proposals pass independent risk checks.")
                            OutlinedTextField(qty,{qty=it},label={Text("Quantity")},modifier=Modifier.fillMaxWidth())
                            OutlinedTextField(orderStop,{orderStop=it},label={Text("Stop price")},modifier=Modifier.fillMaxWidth())
                            Button(onClick={confirm="Submit a simulated $selectedSymbol buy?" to {task {api.call("/paper/orders","POST",JSONObject().put("symbol",selectedSymbol).put("side","buy").put("quantity",qty).put("stop",orderStop).put("idempotency_key",UUID.randomUUID().toString()));refresh()}}},enabled=!busy){Text("Review paper buy")}
                        }
                    }
                    "Agent" -> {
                        Pane("Research intelligence") {
                            Metric("Operation",if(health.optBoolean("worker_online")) "Observing" else "Offline")
                            Text("Strategy: WAIT. No validated executable strategy has been promoted.")
                            Text("Confidence: uncalibrated. Live execution: disabled.")
                            Text("Exchange acknowledgment latency: unavailable. Paper timing is not exchange latency.")
                            Row { Button(onClick={mode("Paused")},enabled=!busy){Text("Pause")};TextButton(onClick={mode("Paper")},enabled=!busy){Text("Resume paper")}}
                        }
                        val events=snapshot.optJSONArray("events") ?: JSONArray()
                        if(events.length()==0) Text("No decisions yet.")
                        events.objects().forEach { e -> Pane(e.getString("kind")) { Text(e.getJSONObject("payload").toString(2),style=MaterialTheme.typography.bodySmall) } }
                    }
                    "Positions" -> {
                        val rows=snapshot.optJSONArray("positions") ?: JSONArray()
                        if(rows.length()==0) Pane("No open positions") {Text("Paper positions appear after an approved simulated trade. Your real exchange funds are untouched.")}
                        rows.objects().sortedBy {it.getString("symbol")}.forEach { row ->
                            Pane("${row.getString("symbol")} • LONG") {
                                Text(row.display("unrealized"),style=MaterialTheme.typography.headlineMedium,color=if(row.optString("unrealized").startsWith("-")) Loss else Emerald)
                                Metric("Quantity",row.display("quantity"));Metric("Entry",row.display("entry"));Metric("Mark",row.display("mark"));Metric("Notional",row.display("notional"));Metric("Mode","SPOT • 1× • PAPER");Metric("SL / TP","${row.display("stop")} / ${row.display("take_profit")}")
                                Text("No spot liquidation. Exits run on backend and may slip or wait during disconnection.",style=MaterialTheme.typography.bodySmall)
                                Row { TextButton(onClick={selectedPosition=row;stop=row.optString("stop","");tp=if(row.isNull("take_profit")) "" else row.optString("take_profit")}){Text("Edit TP/SL")};TextButton(onClick={confirm="Reduce ${row.getString("symbol")} by 50%?" to {reduce(row,"0.5")}}){Text("Reduce 50%")};TextButton(onClick={confirm="Close the entire simulated ${row.getString("symbol")} position?" to {reduce(row,"1")}}){Text("Close")}}
                            }
                        }
                    }
                    "Settings" -> {
                        Pane("Risk limits • paper") {
                            OutlinedTextField(riskTrade,{riskTrade=it},label={Text("Maximum trade loss • $")},modifier=Modifier.fillMaxWidth())
                            OutlinedTextField(riskDaily,{riskDaily=it},label={Text("Maximum daily loss • $")},modifier=Modifier.fillMaxWidth())
                            OutlinedTextField(riskExposure,{riskExposure=it},label={Text("Maximum exposure • $")},modifier=Modifier.fillMaxWidth())
                            Button(onClick={task { val limits=snapshot.getJSONObject("limits");limits.put("max_loss_trade",riskTrade).put("max_daily_loss",riskDaily).put("max_notional",riskExposure).put("max_correlated_notional",riskExposure);api.call("/risk","PUT",limits);refresh() }},enabled=!busy){Text("Save risk limits")}
                            Text("Live derivatives are unavailable in this release. Cross margin can put additional account equity at risk.")
                        }
                        Pane("Connect exchange • read-only") {
                            Text("1 Select exchange → 2 Read-only key → 3 Test balances and capabilities → 4 Encrypt server-side. Trading and withdrawal permissions must be OFF.")
                            OutlinedTextField(exchange,{exchange=it.lowercase()},label={Text("binance / bybit / okx / kraken / coinbase / bitget / kucoin / gate / mexc")},modifier=Modifier.fillMaxWidth())
                            OutlinedTextField(apiKey,{apiKey=it},label={Text("API key")},visualTransformation=PasswordVisualTransformation(),modifier=Modifier.fillMaxWidth())
                            OutlinedTextField(secret,{secret=it},label={Text("API secret")},visualTransformation=PasswordVisualTransformation(),modifier=Modifier.fillMaxWidth())
                            OutlinedTextField(passphrase,{passphrase=it},label={Text("Passphrase, if required")},visualTransformation=PasswordVisualTransformation(),modifier=Modifier.fillMaxWidth())
                            Row { Checkbox(readOnly,{readOnly=it});Text("I disabled trading and withdrawals",modifier=Modifier.padding(top=12.dp)) }
                            Button(onClick={task { api.call("/connections","POST",JSONObject().put("exchange",exchange).put("api_key",apiKey).put("secret",secret).put("passphrase",if(passphrase.isBlank()) JSONObject.NULL else passphrase).put("read_only_attestation",readOnly));apiKey="";secret="";passphrase="";refresh() }},enabled=!busy && readOnly){Text("Test and securely save")}
                            (snapshot.optJSONArray("connections") ?: JSONArray()).objects().forEach { c ->
                                Text("${c.getString("exchange")} • private connectivity tested at save; live disabled")
                                TextButton(onClick={confirm="Remove stored ${c.getString("exchange")} credentials? Revoke the API key on your exchange separately." to {task {api.call("/connections/${c.getString("id")}","DELETE");refresh()}}}){Text("Remove connection")}
                            }
                        }
                        Pane("Account and audit") {
                            Text(email);Text(api.base)
                            Button(onClick={task {share(api.call("/audit/export"))}},enabled=!busy){Text("Export audit JSON")}
                            OutlinedButton(onClick={task {api.call("/auth/logout","POST");api.token="";logged=false;riskLoaded=false;snapshot=JSONObject();markets=JSONArray()}},enabled=!busy){Text("Sign out")}
                        }
                    }
                }
                Spacer(Modifier.height(16.dp))
            }
        }
        confirm?.let { action -> AlertDialog(onDismissRequest={confirm=null},title={Text("Confirm action")},text={Text(action.first)},confirmButton={TextButton(onClick={confirm=null;action.second()}){Text("Confirm")}},dismissButton={TextButton(onClick={confirm=null}){Text("Cancel")}}) }
        selectedPosition?.let { row -> AlertDialog(onDismissRequest={selectedPosition=null},title={Text("Paper TP / SL")},text={Column {OutlinedTextField(stop,{stop=it},label={Text("Stop price")});OutlinedTextField(tp,{tp=it},label={Text("Take profit (optional)")})}},confirmButton={TextButton(onClick={task {api.call("/positions/${row.getString("id")}/exits","PUT",JSONObject().put("stop",stop).put("take_profit",if(tp.isBlank()) JSONObject.NULL else tp));selectedPosition=null;refresh()}}){Text("Save")}},dismissButton={TextButton(onClick={selectedPosition=null}){Text("Cancel")}}) }
    }
}
@Composable fun CandleChart(rows: JSONArray) {
    if(rows.length()==0) {Text("Select Chart to load real exchange candles.");return}
    val data=(0 until rows.length()).takeLast(60).map {i->rows.getJSONArray(i)}
    val low=data.minOf {it.getDouble(3)};val high=data.maxOf {it.getDouble(2)};val span=(high-low).coerceAtLeast(0.00001)
    Canvas(Modifier.fillMaxWidth().height(180.dp)) {
        val step=size.width/data.size
        fun y(p: Double)=((high-p)/span*size.height).toFloat()
        data.forEachIndexed {i,r->val open=r.getDouble(1);val close=r.getDouble(4);val color=if(close>=open) Emerald else Loss;val x=(i+.5f)*step
            drawLine(color,Offset(x,y(r.getDouble(2))),Offset(x,y(r.getDouble(3))),1f)
            drawRect(color,Offset(x-step*.3f,minOf(y(open),y(close))),Size(step*.6f,kotlin.math.abs(y(open)-y(close)).coerceAtLeast(1f)))
        }
    }
}
