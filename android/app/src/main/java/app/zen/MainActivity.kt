package app.zen

import android.os.Bundle
import android.content.Intent
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.repeatOnLifecycle
import org.json.JSONObject
import java.math.RoundingMode
import java.util.UUID

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.setFlags(WindowManager.LayoutParams.FLAG_SECURE,WindowManager.LayoutParams.FLAG_SECURE)
        setContent { ZenApp(share={text->startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply {type="text/plain";putExtra(Intent.EXTRA_TEXT,text)},"Export ZEN history"))}) }
    }
}
enum class ZenTab(val label: String) { HOME("Home"),MARKETS("Markets"),AGENT("Agent"),POSITIONS("Positions"),SETTINGS("Settings") }
data class Confirmation(val title: String,val detail: String,val action: String,val destructive: Boolean=false,val execute: ()->Unit)

@Composable fun ZenApp(repository: ZenRepository?=null,share: (String)->Unit={}) {
    ZenTheme {
        val context=LocalContext.current
        val repo=remember(repository) {repository ?: Api(context)}
        val scope=rememberCoroutineScope()
        val c=remember(repo) {ZenController(repo,scope)}
        var tab by remember {mutableStateOf(ZenTab.HOME)}
        var confirm by remember {mutableStateOf<Confirmation?>(null)}
        var position by remember {mutableStateOf<JSONObject?>(null)}
        var riskDialog by remember {mutableStateOf(false)}
        var exchangeDialog by remember {mutableStateOf(false)}
        var market by remember {mutableStateOf<String?>(null)}
        val lifecycle=LocalLifecycleOwner.current
        LaunchedEffect(c.authorized) {if(c.authorized) lifecycle.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {c.poll()}}
        val mode=c.portfolio.value("mode") ?: "Paper"
        val worker=c.health.optBoolean("worker_online")
        Scaffold(containerColor=ZenColors.Background,topBar={
            if(c.authorized) Column(Modifier.statusBarsPadding().padding(horizontal=22.dp,vertical=12.dp)) {
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically) {
                    Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(10.dp)) {
                        ZenMark(Modifier.size(28.dp))
                        Text("ZEN",style=MaterialTheme.typography.titleLarge,fontWeight=FontWeight.SemiBold)
                    }
                    Row(verticalAlignment=Alignment.CenterVertically) {
                        StatusPill(if(mode=="Emergency Stop") "STOPPED" else "PAPER",if(mode=="Emergency Stop") ZenColors.Red else ZenColors.Blue)
                        IconButton(onClick={confirm=Confirmation("Emergency stop","Prevent all new positions. Existing positions stay open, and their protective exits remain active.","Stop new positions",true){c.mode("Emergency Stop")}},enabled=!c.loading) {
                            Icon(Icons.Rounded.PowerSettingsNew,contentDescription="Emergency stop",tint=ZenColors.Muted)
                        }
                    }
                }
                Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(7.dp)) {
                    Box(Modifier.size(5.dp).background(if(c.connected && worker) ZenColors.Emerald else ZenColors.Muted,RoundedCornerShape(50)))
                    Text(if(c.connected) if(worker) "Backend and observer connected" else "Backend connected · observer offline" else "Connecting to your workspace",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
                }
            }
        },bottomBar={
            if(c.authorized) NavigationBar(containerColor=ZenColors.Background,tonalElevation=0.dp) {
                ZenTab.entries.forEach { page -> NavigationBarItem(modifier=Modifier.testTag("nav-"+page.name),selected=tab==page,onClick={tab=page;market=null},
                    icon={Icon(when(page) {ZenTab.HOME->Icons.Rounded.SpaceDashboard;ZenTab.MARKETS->Icons.Rounded.ShowChart;ZenTab.AGENT->Icons.Rounded.Psychology;ZenTab.POSITIONS->Icons.Rounded.Layers;ZenTab.SETTINGS->Icons.Rounded.Tune},contentDescription=null)},
                    label={Text(page.label,style=MaterialTheme.typography.labelSmall)},
                    colors=NavigationBarItemDefaults.colors(selectedIconColor=ZenColors.Emerald,selectedTextColor=ZenColors.Text,indicatorColor=ZenColors.Raised,unselectedIconColor=ZenColors.Muted,unselectedTextColor=ZenColors.Muted)) }
            }
        }) { padding ->
            Column(Modifier.padding(padding).fillMaxSize()) {
                if(c.loading) LinearProgressIndicator(Modifier.fillMaxWidth(),color=ZenColors.Emerald,trackColor=ZenColors.Surface)
                c.error?.let { text -> FeedbackBanner(text,false,onDismiss={c.clearError()},onRetry=if(c.authorized) ({c.refresh()}) else null) }
                c.notice?.let {text->FeedbackBanner(text,true,onDismiss={c.clearNotice()})}
                if(!c.authorized) WelcomeScreen(c)
                else if(market!=null) MarketDetail(c,market!!,onBack={market=null},onConfirm={confirm=it})
                else when(tab) {
                    ZenTab.HOME->HomeScreen(c,onMarkets={tab=ZenTab.MARKETS},onPositions={tab=ZenTab.POSITIONS},onAgent={tab=ZenTab.AGENT},onRisk={riskDialog=true})
                    ZenTab.MARKETS->MarketsScreen(c,onMarket={symbol->market=symbol;c.chart(symbol,"5m")})
                    ZenTab.AGENT->AgentScreen(c,onConfirm={confirm=it})
                    ZenTab.POSITIONS->PositionsScreen(c,onPosition={position=it},onMarkets={tab=ZenTab.MARKETS})
                    ZenTab.SETTINGS->SettingsScreen(c,onRisk={riskDialog=true},onExchange={exchangeDialog=true},onConfirm={confirm=it},share=share)
                }
            }
        }
        confirm?.let { dialog -> AlertDialog(onDismissRequest={confirm=null},shape=RoundedCornerShape(22.dp),containerColor=ZenColors.Surface,
            title={Text(dialog.title)},text={Text(dialog.detail,color=ZenColors.Muted)},
            confirmButton={TextButton(onClick={confirm=null;dialog.execute()},colors=ButtonDefaults.textButtonColors(contentColor=if(dialog.destructive) ZenColors.Red else ZenColors.Emerald)){Text(dialog.action)}},
            dismissButton={TextButton(onClick={confirm=null}){Text("Cancel")}}) }
        position?.let {p->PositionSheet(c,p,onDismiss={position=null},onConfirm={confirm=it})}
        if(riskDialog) RiskSheet(c,onDismiss={riskDialog=false})
        if(exchangeDialog) ExchangeSheet(c,onDismiss={exchangeDialog=false})
    }
}
@Composable fun FeedbackBanner(text: String,success: Boolean,onDismiss: ()->Unit,onRetry: (()->Unit)?=null) {
    Surface(color=(if(success) ZenColors.Emerald else ZenColors.Red).copy(alpha=.08f)) {
        Row(Modifier.fillMaxWidth().padding(start=20.dp,top=8.dp,bottom=8.dp),verticalAlignment=Alignment.CenterVertically) {
            Text(text,style=MaterialTheme.typography.bodyMedium,modifier=Modifier.weight(1f),color=if(success) ZenColors.Emerald else ZenColors.Red)
            if(onRetry!=null) TextButton(onClick=onRetry){Text("Retry")}
            IconButton(onClick=onDismiss){Icon(Icons.Rounded.Close,contentDescription="Dismiss message",modifier=Modifier.size(18.dp))}
        }
    }
}
@Composable fun WelcomeScreen(c: ZenController) {
    var email by remember {mutableStateOf("")};var password by remember {mutableStateOf("")};var invite by remember {mutableStateOf("")}
    var setup by remember {mutableStateOf(false)};var advanced by remember {mutableStateOf(false)};var server by remember {mutableStateOf(c.repository.base)}
    var passwordVisible by remember {mutableStateOf(false)}
    LaunchedEffect(c.authorized) {if(c.authorized) {password="";invite=""}}
    LazyColumn(Modifier.fillMaxSize(),contentPadding=PaddingValues(horizontal=24.dp,vertical=28.dp),verticalArrangement=Arrangement.spacedBy(24.dp)) {
        item {
            Spacer(Modifier.height(18.dp));ZenMark(Modifier.size(54.dp));Spacer(Modifier.height(22.dp))
            Text("Clarity before\nevery trade.",style=MaterialTheme.typography.displaySmall)
            Spacer(Modifier.height(12.dp))
            Text("Your markets, decisions and risk —\nin one calm workspace.",style=MaterialTheme.typography.bodyLarge,color=ZenColors.Muted)
        }
        item {SurfaceCard {
            SectionLabel(if(setup) "Create your workspace" else "Welcome back")
            Text(if(setup) "Use your private setup code to create the owner account." else "Sign in to your secure ZEN workspace.",color=ZenColors.Muted,style=MaterialTheme.typography.bodyMedium)
            ZenField("Owner email",email,{email=it},placeholder="you@example.com")
            OutlinedTextField(password,{password=it},label={Text("Password")},singleLine=true,modifier=Modifier.fillMaxWidth(),shape=RoundedCornerShape(12.dp),visualTransformation=if(passwordVisible) VisualTransformation.None else PasswordVisualTransformation(),trailingIcon={IconButton(onClick={passwordVisible=!passwordVisible}){Icon(if(passwordVisible) Icons.Rounded.VisibilityOff else Icons.Rounded.Visibility,contentDescription=if(passwordVisible) "Hide password" else "Show password")}})
            if(setup) ZenField("Setup code",invite,{invite=it},secret=true)
            PrimaryAction(if(setup) "Create workspace" else "Sign in",enabled=!c.loading && email.isNotBlank() && password.isNotBlank() && (!setup || invite.isNotBlank())) {
                if(setup) c.setup(email,password,invite,server) else c.login(email,password,server)
            }
            TextButton(onClick={setup=!setup},modifier=Modifier.align(Alignment.CenterHorizontally)) {Text(if(setup) "Already have an account? Sign in" else "First time? Create workspace")}
        }}
        item {Row(horizontalArrangement=Arrangement.spacedBy(10.dp),verticalAlignment=Alignment.CenterVertically) {
            Icon(Icons.Rounded.Lock,contentDescription=null,tint=ZenColors.Muted,modifier=Modifier.size(18.dp))
            Text("Encrypted session on your device. Exchange credentials stay on the server.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
        }}
        item {Column {
            Text("Paper mode is the starting point. No real-money orders are sent in this release.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
            TextButton(onClick={advanced=!advanced},contentPadding=PaddingValues(0.dp)){Text(if(advanced) "Hide connection settings" else "Connection settings",style=MaterialTheme.typography.bodySmall)}
            if(advanced) ZenField("HTTPS backend URL",server,{server=it})
        }}
    }
}
@Composable fun ZenField(label: String,value: String,onChange: (String)->Unit,placeholder: String="",secret: Boolean=false) {
    OutlinedTextField(value,onChange,label={Text(label)},placeholder=if(placeholder.isEmpty()) null else ({Text(placeholder)}),singleLine=true,
        visualTransformation=if(secret) PasswordVisualTransformation() else VisualTransformation.None,modifier=Modifier.fillMaxWidth(),shape=RoundedCornerShape(12.dp))
}
@Composable fun PageHeading(title: String,subtitle: String) {
    Column(verticalArrangement=Arrangement.spacedBy(5.dp)) {Text(title,style=MaterialTheme.typography.headlineMedium);Text(subtitle,style=MaterialTheme.typography.bodyMedium,color=ZenColors.Muted)}
}
@Composable fun HomeScreen(c: ZenController,onMarkets: ()->Unit,onPositions: ()->Unit,onAgent: ()->Unit,onRisk: ()->Unit) {
    val p=c.portfolio
    LazyColumn(Modifier.fillMaxSize(),contentPadding=PaddingValues(22.dp,16.dp,22.dp,24.dp),verticalArrangement=Arrangement.spacedBy(18.dp)) {
        item {PageHeading("Overview","Your paper portfolio, at a glance.")}
        item {SurfaceCard {
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {Eyebrow("Paper equity");Text("USDT",style=MaterialTheme.typography.labelSmall,color=ZenColors.Muted)}
            Text(money(p.value("equity")),style=MaterialTheme.typography.displaySmall)
            Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                Text(signedMoney(p.value("net_pnl")),color=pnlColor(p.value("net_pnl")),fontFamily=FontFamily.Monospace,style=MaterialTheme.typography.titleMedium)
                Text("since start",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
            }
            HorizontalDivider(color=ZenColors.Border)
            Row(Modifier.fillMaxWidth()) {MiniMetric("Available cash",money(p.value("cash")),modifier=Modifier.weight(1f));MiniMetric("Today · net P&L",signedMoney(p.value("daily_net")),pnlColor(p.value("daily_net")),Modifier.weight(1f))}
            if(p.optBoolean("stale")) Text("Prices are stale. Portfolio valuation will resume when fresh quotes arrive.",color=ZenColors.Red,style=MaterialTheme.typography.bodySmall)
        }}
        item {Row(horizontalArrangement=Arrangement.spacedBy(12.dp)) {
            OutlinedButton(onClick=onMarkets,modifier=Modifier.weight(1f).heightIn(min=48.dp),shape=RoundedCornerShape(13.dp)){Icon(Icons.Rounded.ShowChart,null,Modifier.size(18.dp));Spacer(Modifier.width(8.dp));Text("Markets")}
            OutlinedButton(onClick=onPositions,modifier=Modifier.weight(1f).heightIn(min=48.dp),shape=RoundedCornerShape(13.dp)){Icon(Icons.Rounded.Layers,null,Modifier.size(18.dp));Spacer(Modifier.width(8.dp));Text("Positions")}
        }}
        item {SurfaceCard {
            SectionLabel("Agent") {StatusPill(if(c.health.optBoolean("worker_online")) "OBSERVING" else "OFFLINE",if(c.health.optBoolean("worker_online")) ZenColors.Emerald else ZenColors.Muted)}
            Text(c.agent.value("summary") ?: "Waiting for fresh market observations.",style=MaterialTheme.typography.bodyLarge)
            Text(c.agent.value("reason") ?: "Trading proposals need validated evidence and independent risk approval.",style=MaterialTheme.typography.bodyMedium,color=ZenColors.Muted)
            TextButton(onClick=onAgent,contentPadding=PaddingValues(0.dp)){Text("View agent activity");Spacer(Modifier.width(5.dp));Icon(Icons.Rounded.ArrowForward,null,Modifier.size(16.dp))}
        }}
        item {SurfaceCard {
            SectionLabel("Risk allocation") {TextButton(onClick=onRisk,contentPadding=PaddingValues(0.dp)){Text("Manage")}}
            val exposure=p.value("exposure")?.toDoubleOrNull();val maximum=c.limits.value("max_notional")?.toDoubleOrNull()
            KeyValue("Exposure",if(exposure==null) "—" else "${money(p.value("exposure"))} / ${money(c.limits.value("max_notional"))}")
            LinearProgressIndicator(progress={if(exposure!=null && maximum!=null && maximum>0) (exposure/maximum).toFloat().coerceIn(0f,1f) else 0f},modifier=Modifier.fillMaxWidth().height(4.dp),color=ZenColors.Blue,trackColor=ZenColors.Raised)
            KeyValue("Loss budget per trade",money(c.limits.value("max_loss_trade")))
            KeyValue("Daily loss limit",money(c.limits.value("max_daily_loss")))
        }}
        item {SurfaceCard {
            SectionLabel("Personal objective")
            KeyValue("Aspirational daily target",money(p.value("target")))
            Text("A personal goal, never a reason to force a trade. Returns are not guaranteed.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
        }}
        if(c.events.length()>0) item {SectionLabel("Recent activity");Spacer(Modifier.height(10.dp));ActivityRow(c.events.getJSONObject(0))}
    }
}
@Composable fun MarketsScreen(c: ZenController,onMarket: (String)->Unit) {
    var search by remember {mutableStateOf("")};var favoritesOnly by remember {mutableStateOf(false)}
    val context=LocalContext.current;val prefs=remember {context.getSharedPreferences("zen_preferences",android.content.Context.MODE_PRIVATE)}
    var favorites by remember {mutableStateOf(prefs.getStringSet("favorites",emptySet()).orEmpty().toSet())}
    val rows=c.markets.rows().filter {m-> val symbol=m.getJSONObject("quote").getString("symbol");symbol.contains(search,true) && (!favoritesOnly || symbol in favorites)}
    LazyColumn(Modifier.fillMaxSize(),contentPadding=PaddingValues(22.dp,16.dp,22.dp,24.dp),verticalArrangement=Arrangement.spacedBy(14.dp)) {
        item {PageHeading("Markets","Fresh observations. No predicted prices.")}
        item {OutlinedTextField(search,{search=it},placeholder={Text("Search markets")},leadingIcon={Icon(Icons.Rounded.Search,null)},singleLine=true,modifier=Modifier.fillMaxWidth(),shape=RoundedCornerShape(14.dp))}
        item {Row(horizontalArrangement=Arrangement.spacedBy(10.dp)) {FilterChip(!favoritesOnly,{favoritesOnly=false},label={Text("All markets")});FilterChip(favoritesOnly,{favoritesOnly=true},label={Text("Watchlist")})}}
        if(rows.isEmpty()) item {EmptyState(if(favoritesOnly) "Your watchlist is empty" else "No market observations","${if(favoritesOnly) "Tap a star to save a market." else "Fresh prices appear when the backend observer connects."}",if(!favoritesOnly) "Refresh" else null){c.refresh()}}
        items(rows,key={it.getJSONObject("quote").getString("symbol")}) {m ->
            val q=m.getJSONObject("quote");val symbol=q.getString("symbol")
            SurfaceCard {Row(verticalAlignment=Alignment.CenterVertically) {
                Box(Modifier.size(42.dp).background(ZenColors.Raised,RoundedCornerShape(13.dp)),contentAlignment=Alignment.Center){Text(symbol.substringBefore('/').take(1),color=ZenColors.Blue,style=MaterialTheme.typography.titleLarge)}
                Column(Modifier.weight(1f).padding(start=12.dp).clickable {onMarket(symbol)}) {
                    Text(symbol.substringBefore('/'),style=MaterialTheme.typography.titleMedium)
                    Text("${symbol.substringAfter('/')} · Spot",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
                }
                Column(horizontalAlignment=Alignment.End,modifier=Modifier.clickable {onMarket(symbol)}) {
                    Text("$"+number(q.value("last")),fontFamily=FontFamily.Monospace,style=MaterialTheme.typography.titleMedium)
                    Text(if(m.optBoolean("stale")) "STALE" else q.value("change_percent")?.let {number(it)+"%"} ?: "Change unavailable",color=if(m.optBoolean("stale")) ZenColors.Muted else pnlColor(q.value("change_percent")),style=MaterialTheme.typography.bodySmall)
                }
                IconButton(onClick={favorites=if(symbol in favorites) favorites-symbol else favorites+symbol;prefs.edit().putStringSet("favorites",favorites).apply()}){Icon(if(symbol in favorites) Icons.Rounded.Star else Icons.Rounded.StarBorder,contentDescription=if(symbol in favorites) "Remove $symbol from watchlist" else "Add $symbol to watchlist",tint=if(symbol in favorites) ZenColors.Blue else ZenColors.Muted,modifier=Modifier.size(20.dp))}
            }
            TextButton(onClick={onMarket(symbol)},contentPadding=PaddingValues(0.dp)){Text("Open market");Spacer(Modifier.width(5.dp));Icon(Icons.Rounded.ChevronRight,null,Modifier.size(16.dp))}
            }
        }
    }
}
@Composable fun AgentScreen(c: ZenController,onConfirm: (Confirmation)->Unit) {
    val mode=c.portfolio.value("mode");val paused=mode!="Paper"
    val decisions=c.events.rows().filter {it.value("kind")=="decision"}
    LazyColumn(Modifier.fillMaxSize(),contentPadding=PaddingValues(22.dp,16.dp,22.dp,24.dp),verticalArrangement=Arrangement.spacedBy(18.dp)) {
        item {PageHeading("Intelligence","What ZEN observes, and why it waits.")}
        item {SurfaceCard {
            SectionLabel("Current state") {StatusPill(if(paused) "PAUSED" else if(c.health.optBoolean("worker_online")) "OBSERVING" else "OFFLINE")}
            Text(c.agent.value("summary") ?: "Collecting market context",style=MaterialTheme.typography.titleLarge)
            Text(c.agent.value("reason") ?: "There is no validated execution strategy to deploy yet.",color=ZenColors.Muted)
            KeyValue("Decision",c.agent.value("action") ?: "WAIT")
            KeyValue("Model",c.agent.value("version") ?: "Research v1")
            KeyValue("Calibration", "Not established")
            PrimaryAction(if(paused) "Resume paper workspace" else "Pause new positions",enabled=!c.loading) {
                onConfirm(Confirmation(if(paused) "Resume paper workspace" else "Pause new positions",if(paused) "Enable risk-approved paper orders. Research strategies remain gated by validation." else "Prevent new paper positions. Existing protective exits remain active.",if(paused) "Resume paper" else "Pause"){c.mode(if(paused) "Paper" else "Paused")})
            }
        }}
        item {SectionLabel("Market assessments")}
        if(decisions.isEmpty()) item {EmptyState("No assessments yet","The research worker will record observations after account setup. A quiet agent is a valid state.")}
        items(decisions.take(6),key={it.getString("id")}) {e->val d=e.getJSONObject("payload");SurfaceCard {
            SectionLabel(d.value("symbol") ?: "Market") {StatusPill(d.value("action") ?: "WAIT")}
            Text(d.value("reason") ?: "Awaiting validated evidence",style=MaterialTheme.typography.bodyMedium,color=ZenColors.Muted)
            val evidence=d.optJSONArray("evidence")
            if(evidence!=null && evidence.length()>0) {Eyebrow("Observed evidence");for(i in 0 until evidence.length()) Text(evidence.getString(i),style=MaterialTheme.typography.bodyMedium)}
            val contrary=d.optJSONArray("contradictions")
            if(contrary!=null && contrary.length()>0) {Eyebrow("Limits to the conclusion");for(i in 0 until contrary.length()) Text(contrary.getString(i),style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}
        }}
        item {SectionLabel("Audit trail")}
        items(c.events.rows().filter {it.value("kind")!="decision"}.take(10),key={it.getString("id")}) {ActivityRow(it)}
        item {Text("Research is separated from execution. Every order must pass independent risk checks. Exchange latency is unavailable while live execution is disabled.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}
    }
}
@Composable fun ActivityRow(event: JSONObject) {
    val payload=event.optJSONObject("payload") ?: JSONObject()
    val kind=event.value("kind")
    val title=when(kind) {"paper_fill"->"Paper order completed";"risk_veto"->"Opportunity withheld";"risk_limits"->"Risk limits updated";"mode"->"Workspace ${payload.value("mode")?.lowercase()}";"login"->"Signed in";"owner_provisioned"->"Workspace created";"connection_added"->"Exchange connected";"connection_removed"->"Connection removed";"paper_exits"->"Protective exits updated";else->kind?.replace('_',' ')?.replaceFirstChar {it.uppercase()} ?: "Activity"}
    Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.Top,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
        Icon(if(kind=="risk_veto") Icons.Rounded.Shield else Icons.Rounded.History,contentDescription=null,tint=if(kind=="risk_veto") ZenColors.Blue else ZenColors.Muted,modifier=Modifier.size(18.dp).padding(top=2.dp))
        Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(3.dp)) {
            Text(title,style=MaterialTheme.typography.bodyMedium)
            (payload.value("reason") ?: payload.value("symbol"))?.let {Text(it,style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}
        }
        val timestamp=event.optDouble("created",0.0)
        if(timestamp>0) Text(java.text.SimpleDateFormat("HH:mm",java.util.Locale.getDefault()).format(java.util.Date((timestamp*1000).toLong())),style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
    }
}
@Composable fun PositionsScreen(c: ZenController,onPosition: (JSONObject)->Unit,onMarkets: ()->Unit) {
    val rows=c.positions.rows().sortedBy {it.getString("symbol")}
    LazyColumn(Modifier.fillMaxSize(),contentPadding=PaddingValues(22.dp,16.dp,22.dp,24.dp),verticalArrangement=Arrangement.spacedBy(16.dp)) {
        item {PageHeading("Positions","Every exposure, clearly accounted for.")}
        if(rows.isEmpty()) item {EmptyState("No open positions","Approved paper orders appear here. Your connected exchange balances are untouched.","Explore markets",onMarkets)}
        items(rows,key={it.getString("id")}) {p->SurfaceCard {
            SectionLabel(p.getString("symbol")) {StatusPill("LONG · SPOT",ZenColors.Blue)}
            Text(signedMoney(p.value("unrealized")),style=MaterialTheme.typography.headlineMedium,color=pnlColor(p.value("unrealized")),fontFamily=FontFamily.Monospace)
            Text("Unrealized P&L",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
            Row(Modifier.fillMaxWidth()) {MiniMetric("Entry",money(p.value("entry")),modifier=Modifier.weight(1f));MiniMetric("Current mark",money(p.value("mark")),modifier=Modifier.weight(1f))}
            HorizontalDivider(color=ZenColors.Border)
            KeyValue("Exposure",money(p.value("notional")));KeyValue("Stop / take profit","${number(p.value("stop"))} / ${number(p.value("take_profit"))}")
            if(p.optBoolean("stale")) Text("Market price is stale. Closing needs a fresh quote.",color=ZenColors.Red,style=MaterialTheme.typography.bodySmall)
            PrimaryAction("Manage position",enabled=!c.loading){onPosition(p)}
        }}
    }
}
@Composable fun SettingsScreen(c: ZenController,onRisk: ()->Unit,onExchange: ()->Unit,onConfirm: (Confirmation)->Unit,share: (String)->Unit) {
    LazyColumn(Modifier.fillMaxSize(),contentPadding=PaddingValues(22.dp,16.dp,22.dp,24.dp),verticalArrangement=Arrangement.spacedBy(18.dp)) {
        item {PageHeading("Workspace","Connections, security and control.")}
        item {SurfaceCard {
            Eyebrow("Account")
            Text(c.snapshot.optJSONObject("account")?.value("email") ?: "Owner workspace",style=MaterialTheme.typography.titleMedium)
            Text("Session protected by Android Keystore. Your password is not stored.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
        }}
        item {SurfaceCard {
            SettingsRow("Risk limits","Exposure, loss budgets and protective controls",Icons.Rounded.Shield,onRisk)
            HorizontalDivider(color=ZenColors.Border)
            SettingsRow("Exchange connections","Read-only access. No withdrawal permissions.",Icons.Rounded.Link,onExchange)
        }}
        if(c.connections.length()>0) item {SurfaceCard {
            Eyebrow("Connected exchanges")
            c.connections.rows().forEach {connection->Row(verticalAlignment=Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {Text(connection.getString("exchange").replaceFirstChar {it.uppercase()},style=MaterialTheme.typography.titleMedium);Text("Credentials encrypted on server",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}
                TextButton(onClick={onConfirm(Confirmation("Remove connection","Remove stored credentials from ZEN. Revoke the API key on the exchange separately.","Remove",true){c.removeConnection(connection.getString("id"))})}) {Text("Remove",color=ZenColors.Red)}
            }}
        }}
        item {SurfaceCard {
            SectionLabel("Trading environment") {StatusPill("PAPER")}
            Text("Paper trades use real market observations and simulated capital. Live trading is locked until execution and operational reviews are complete.",style=MaterialTheme.typography.bodyMedium,color=ZenColors.Muted)
            KeyValue("Leverage","1× · spot");KeyValue("Backend",if(c.connected) "Connected" else "Disconnected");KeyValue("Observer",if(c.health.optBoolean("worker_online")) "Online" else "Offline")
            TextButton(onClick={c.refresh()},enabled=!c.loading,contentPadding=PaddingValues(0.dp)){Text("Check connection")}
        }}
        item {SurfaceCard {SettingsRow("Export activity","Save your audit history as JSON",Icons.Rounded.FileDownload){c.export(share)}}}
        item {OutlinedButton(onClick={onConfirm(Confirmation("Sign out","Revoke this session and remove its encrypted token from this device.","Sign out"){c.logout()})},enabled=!c.loading,shape=RoundedCornerShape(14.dp),modifier=Modifier.fillMaxWidth().heightIn(min=48.dp)){Text("Sign out")}}
        item {Text("ZEN ${BuildConfig.VERSION_NAME}\nYour capital stays on your exchange.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}
    }
}
@Composable fun SettingsRow(title: String,description: String,icon: androidx.compose.ui.graphics.vector.ImageVector,onClick: ()->Unit) {
    Row(Modifier.fillMaxWidth().clickable(onClick=onClick).heightIn(min=60.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
        Icon(icon,null,tint=ZenColors.Blue,modifier=Modifier.size(21.dp))
        Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(3.dp)) {Text(title,style=MaterialTheme.typography.titleMedium);Text(description,style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}
        Icon(Icons.Rounded.ChevronRight,null,tint=ZenColors.Muted)
    }
}
