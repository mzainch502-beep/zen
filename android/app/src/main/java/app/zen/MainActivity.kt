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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.sp
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.Role
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
enum class ZenTab(val label: String) { HOME("Home"),PORTFOLIO("Portfolio"),TRADE("Trade"),AI("AI"),MORE("More") }
data class Confirmation(val title: String,val detail: String,val action: String,val destructive: Boolean=false,val execute: ()->Unit)

@Composable fun ZenApp(repository: ZenRepository?=null,share: (String)->Unit={}) {
    val context=LocalContext.current
    val prefs=remember {context.getSharedPreferences("zen_preferences",android.content.Context.MODE_PRIVATE)}
    var light by remember {mutableStateOf(prefs.getBoolean("light_theme",false))}
    SideEffect {(context as? android.app.Activity)?.let {activity->if(android.os.Build.VERSION.SDK_INT>=29) activity.window.isNavigationBarContrastEnforced=false;activity.window.navigationBarColor=android.graphics.Color.parseColor(if(light) "#F4F7FB" else "#080D18");androidx.core.view.WindowInsetsControllerCompat(activity.window,activity.window.decorView).apply {isAppearanceLightStatusBars=light;isAppearanceLightNavigationBars=light}}}
    ZenTheme(light=light) {
        val repo=remember(repository) {repository ?: Api(context)}
        val scope=rememberCoroutineScope()
        val c=remember(repo) {ZenController(repo,scope)}
        var tab by remember {mutableStateOf(ZenTab.HOME)}
        var confirm by remember {mutableStateOf<Confirmation?>(null)}
        var position by remember {mutableStateOf<JSONObject?>(null)}
        var riskDialog by remember {mutableStateOf(false)}
        var exchangeDialog by remember {mutableStateOf(false)}
        var market by remember {mutableStateOf<String?>(null)}
        var section by remember {mutableStateOf("More")}
        var capitalDialog by remember {mutableStateOf(false)}
        var tradingDialog by remember {mutableStateOf(false)}
        val lifecycle=LocalLifecycleOwner.current
        LaunchedEffect(c.authorized) {if(c.authorized) lifecycle.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {c.poll()}}
        val mode=c.portfolio.value("mode") ?: "Paper"
        val worker=c.health.optBoolean("worker_online")
        Scaffold(containerColor=ZenColors.Background,topBar={
            if(c.authorized) Surface(color=ZenColors.Header) {
                Column(Modifier.statusBarsPadding().padding(horizontal=16.dp,vertical=4.dp)) {
                    Row(Modifier.fillMaxWidth().height(48.dp),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically) {
                        Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(8.dp)){ZenMark(Modifier.size(30.dp));Text("ZEN",style=MaterialTheme.typography.titleLarge,fontWeight=FontWeight.SemiBold,letterSpacing=2.sp)}
                        Row {
                            DeskIconButton(R.drawable.ic_nav_notifications,"Notifications"){section="Alerts";tab=ZenTab.MORE}
                            DeskIconButton(R.drawable.ic_nav_account,"Account"){section="Account";tab=ZenTab.MORE}
                            DeskIconButton(R.drawable.ic_nav_menu,"Open menu"){section="More";tab=ZenTab.MORE}
                            DeskIconButton(R.drawable.ic_nav_power,"Emergency stop",tint=ZenColors.Red){confirm=Confirmation("Emergency trading halt","Prevent new entries. Existing protective exits and close-only actions remain active.","Halt entries",true){c.mode("Emergency Stop")}}
                        }
                    }
                    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                        Text(if(c.connected && worker) "● Market data connected" else if(c.connected) "Observer offline" else "Disconnected",style=MaterialTheme.typography.bodySmall,color=if(c.connected && worker) ZenColors.Emerald else ZenColors.Warning)
                        Text(if(!c.portfolio.optBoolean("paper",true)) if(mode=="Paused") "LIVE · PAUSED" else if(mode=="Emergency Stop") "LIVE · STOPPED" else "LIVE" else "PAPER · "+(c.portfolio.value("product") ?: "spot").uppercase(),style=MaterialTheme.typography.labelSmall,color=if(!c.portfolio.optBoolean("paper",true)) ZenColors.Red else ZenColors.Gold)
                    }
                }
            }
        },bottomBar={
            if(c.authorized) Surface(color=ZenColors.Background,modifier=Modifier.navigationBarsPadding()) {
                Row(Modifier.fillMaxWidth().padding(horizontal=4.dp,vertical=6.dp)) {
                    ZenTab.entries.forEach {page->
                        Column(Modifier.weight(1f).heightIn(min=56.dp).background(if(tab==page) ZenColors.Emerald.copy(alpha=.08f) else Color.Transparent,RoundedCornerShape(12.dp)).testTag("nav-"+page.name).semantics {selected=tab==page;role=Role.Tab}.clickable {tab=page;market=null;if(page==ZenTab.MORE)section="More"},horizontalAlignment=Alignment.CenterHorizontally,verticalArrangement=Arrangement.Center) {
                            Icon(androidx.compose.ui.res.painterResource(when(page){ZenTab.HOME->R.drawable.ic_nav_home;ZenTab.PORTFOLIO->R.drawable.ic_nav_portfolio;ZenTab.TRADE->R.drawable.ic_nav_trade;ZenTab.AI->R.drawable.ic_nav_ai;ZenTab.MORE->R.drawable.ic_nav_more}),null,tint=if(tab==page) ZenColors.Emerald else ZenColors.Muted,modifier=Modifier.size(22.dp))
                            Spacer(Modifier.height(5.dp))
                            Text(page.label,maxLines=1,softWrap=false,style=MaterialTheme.typography.labelSmall.copy(fontSize=12.sp,letterSpacing=0.sp),color=if(tab==page) ZenColors.Text else ZenColors.Muted)
                        }
                    }
                }
            }
        }) { padding ->
            Column(Modifier.padding(padding).fillMaxSize()) {
                if(c.authorized) AutomationControl(c,onConfirm={confirm=it})
                if(c.loading) LinearProgressIndicator(Modifier.fillMaxWidth(),color=ZenColors.Emerald,trackColor=ZenColors.Surface)
                c.error?.let { text -> FeedbackBanner(text,false,onDismiss={c.clearError()},onRetry=if(c.authorized) ({c.refresh()}) else null) }
                c.notice?.let {text->FeedbackBanner(text,true,onDismiss={c.clearNotice()})}
                if(!c.authorized) WelcomeScreen(c)
                else if(market!=null) MarketDetail(c,market!!,onBack={market=null},onConfirm={confirm=it})
                else when(tab) {
                    ZenTab.HOME->ExecutiveHome(c,onCapital={capitalDialog=true},onMarkets={tab=ZenTab.TRADE},onPortfolio={tab=ZenTab.PORTFOLIO},onAI={tab=ZenTab.AI})
                    ZenTab.TRADE->MarketsScreen(c,onMarket={symbol->market=symbol;c.chart(symbol,"5m")})
                    ZenTab.AI->AgentScreen(c,onConfirm={confirm=it})
                    ZenTab.PORTFOLIO->PortfolioDesk(c,onPosition={position=it},onMarkets={tab=ZenTab.TRADE})
                    ZenTab.MORE->MoreDesk(c,section,onSection={when(it){"Portfolio"->tab=ZenTab.PORTFOLIO;"Markets","Trading Desk"->tab=ZenTab.TRADE;"AI Intelligence"->tab=ZenTab.AI;else->section=it}},light=light,onTheme={light=it;prefs.edit().putBoolean("light_theme",it).apply()},onRisk={tradingDialog=true},onExchange={exchangeDialog=true},onTrading={tradingDialog=true},onCapital={capitalDialog=true},onConfirm={confirm=it},share=share)

                }
            }
        }
        confirm?.let { dialog -> AlertDialog(onDismissRequest={confirm=null},shape=RoundedCornerShape(22.dp),containerColor=ZenColors.Surface,
            title={Text(dialog.title)},text={Text(dialog.detail,color=ZenColors.Muted)},
            confirmButton={TextButton(onClick={confirm=null;dialog.execute()},colors=ButtonDefaults.textButtonColors(contentColor=if(dialog.destructive) ZenColors.Red else ZenColors.Emerald)){Text(dialog.action)}},
            dismissButton={TextButton(onClick={confirm=null}){Text("Cancel")}}) }
        position?.let {p->PositionSheet(c,p,onDismiss={position=null},onConfirm={confirm=it})}
        if(capitalDialog) CapitalSheet(c,onDismiss={capitalDialog=false},onConfirm={confirm=it})
        if(riskDialog) RiskSheet(c,onDismiss={riskDialog=false})
        if(exchangeDialog) ExchangeSheet(c,onDismiss={exchangeDialog=false})
        if(tradingDialog) FuturesSettingsSheet(c,onDismiss={tradingDialog=false},onConfirm={confirm=it})
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
    LazyColumn(Modifier.fillMaxSize(),contentPadding=PaddingValues(horizontal=24.dp,vertical=16.dp),verticalArrangement=Arrangement.spacedBy(20.dp)) {
        item {
            Spacer(Modifier.height(4.dp));Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(14.dp)){ZenMark(Modifier.size(44.dp));Column {Text("ZEN",style=MaterialTheme.typography.headlineMedium,fontWeight=FontWeight.SemiBold);Eyebrow("Trading intelligence")}};Spacer(Modifier.height(20.dp))
            Text("The investment\noperating system.",style=MaterialTheme.typography.displaySmall.copy(fontSize=30.sp,lineHeight=36.sp,fontWeight=FontWeight.SemiBold))
            Spacer(Modifier.height(12.dp))
            Text("Markets. Decisions. Capital.",style=MaterialTheme.typography.bodyLarge,color=ZenColors.Muted)
        }
        item {SurfaceCard {
            SectionLabel(if(setup) "Create workspace" else "Welcome back") {
                TextButton(onClick={setup=!setup},contentPadding=PaddingValues(horizontal=8.dp)) {Text(if(setup) "Sign in" else "Create account")}
            }
            if(setup) Text("Use your private owner setup code.",color=ZenColors.Muted,style=MaterialTheme.typography.bodyMedium)
            ZenField("Owner email",email,{email=it},placeholder="you@example.com")
            OutlinedTextField(password,{password=it},label={Text("Password")},singleLine=true,modifier=Modifier.fillMaxWidth().testTag("password-input"),shape=RoundedCornerShape(12.dp),visualTransformation=if(passwordVisible) VisualTransformation.None else PasswordVisualTransformation(),trailingIcon={IconButton(onClick={passwordVisible=!passwordVisible}){Icon(if(passwordVisible) Icons.Rounded.VisibilityOff else Icons.Rounded.Visibility,contentDescription=if(passwordVisible) "Hide password" else "Show password")}})
            if(setup) ZenField("Setup code",invite,{invite=it},secret=true)
            PrimaryAction(if(setup) "Create workspace" else "Sign in",enabled=!c.loading && email.isNotBlank() && password.isNotBlank() && (!setup || invite.isNotBlank())) {
                if(setup) c.setup(email,password,invite,server) else c.login(email,password,server)
            }
        }}
        item {Row(horizontalArrangement=Arrangement.spacedBy(10.dp),verticalAlignment=Alignment.CenterVertically) {
            Icon(Icons.Rounded.Lock,contentDescription=null,tint=ZenColors.Muted,modifier=Modifier.size(18.dp))
            Text("Encrypted session on your device. Exchange credentials stay on the server.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
        }}
        item {Column {
            Text("Starts in paper mode. Live futures requires your separate account authorization.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
            TextButton(onClick={advanced=!advanced},contentPadding=PaddingValues(0.dp)){Text(if(advanced) "Hide connection settings" else "Connection settings",style=MaterialTheme.typography.bodySmall)}
            if(advanced) ZenField("HTTPS backend URL",server,{server=it})
        }}
    }
}
@Composable fun ZenField(label: String,value: String,onChange: (String)->Unit,placeholder: String="",secret: Boolean=false) {
    OutlinedTextField(value,onChange,label={Text(label)},placeholder=if(placeholder.isEmpty()) null else ({Text(placeholder)}),singleLine=true,
        visualTransformation=if(secret) PasswordVisualTransformation() else VisualTransformation.None,modifier=Modifier.fillMaxWidth().testTag("field-"+label),shape=RoundedCornerShape(12.dp))
}
@Composable fun PageHeading(title: String,subtitle: String) {
    Column(verticalArrangement=Arrangement.spacedBy(5.dp)) {Text(title,style=MaterialTheme.typography.headlineMedium);Text(subtitle,style=MaterialTheme.typography.bodyMedium,color=ZenColors.Muted)}
}
@Composable fun MarketsScreen(c: ZenController,onMarket: (String)->Unit) {
    var search by remember {mutableStateOf("")};var favoritesOnly by remember {mutableStateOf(false)}
    val context=LocalContext.current;val prefs=remember {context.getSharedPreferences("zen_preferences",android.content.Context.MODE_PRIVATE)}
    var favorites by remember {mutableStateOf(prefs.getStringSet("favorites",emptySet()).orEmpty().toSet())}
    var category by remember {mutableStateOf("All")}
    var sort by remember {mutableStateOf("Liquidity")}
    val rows=c.markets.rows().filter {m-> val symbol=m.getJSONObject("quote").getString("symbol");symbol.contains(search,true) && (!favoritesOnly || symbol in favorites) && (category=="All" || (category=="Stock-linked" && m.optJSONObject("instrument")?.value("kind") in listOf("stock_linked_perpetual","index_linked_perpetual")) || (category=="Crypto" && m.optJSONObject("instrument")?.value("kind") !in listOf("stock_linked_perpetual","index_linked_perpetual")))}.sortedByDescending {m->if(sort=="Gainers") m.getJSONObject("quote").value("change_percent")?.toDoubleOrNull() ?: 0.0 else m.optJSONObject("ticker")?.value("amount24")?.toDoubleOrNull() ?: 0.0}
    LazyColumn(Modifier.fillMaxSize(),contentPadding=PaddingValues(22.dp,16.dp,22.dp,24.dp),verticalArrangement=Arrangement.spacedBy(14.dp)) {
        item {PageHeading("Markets","${c.markets.length()} instruments · live exchange catalogue")}
        item {OutlinedTextField(search,{search=it},placeholder={Text("Search markets")},leadingIcon={Icon(Icons.Rounded.Search,null)},singleLine=true,modifier=Modifier.fillMaxWidth(),shape=RoundedCornerShape(14.dp))}
        item {Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(8.dp)) {FilterChip(!favoritesOnly && sort=="Liquidity",{favoritesOnly=false;sort="Liquidity"},label={Text("Liquidity")});FilterChip(!favoritesOnly && sort=="Gainers",{favoritesOnly=false;sort="Gainers"},label={Text("Gainers")});FilterChip(favoritesOnly,{favoritesOnly=true},label={Text("Watchlist")})}}
        item {Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(8.dp)){listOf("All","Crypto","Stock-linked").forEach {cat->FilterChip(category==cat,{category=cat},label={Text(cat)})}}}
        if(rows.isEmpty()) item {EmptyState(if(favoritesOnly) "Your watchlist is empty" else "No market observations","${if(favoritesOnly) "Tap a star to save a market." else "Fresh prices appear when the backend observer connects."}",if(!favoritesOnly) "Refresh" else null){c.refresh()}}
        items(rows,key={it.getJSONObject("quote").getString("symbol")}) {m ->
            val q=m.getJSONObject("quote");val symbol=q.getString("symbol")
            Surface(color=ZenColors.Surface,shape=RoundedCornerShape(12.dp)) {Row(Modifier.fillMaxWidth().padding(horizontal=12.dp,vertical=8.dp).clickable {onMarket(symbol)}.heightIn(min=52.dp),verticalAlignment=Alignment.CenterVertically) {
                Box(Modifier.size(42.dp).background(ZenColors.Raised,RoundedCornerShape(13.dp)),contentAlignment=Alignment.Center){Text(symbol.substringBefore('/').substringBefore('_').take(1),color=ZenColors.Blue,style=MaterialTheme.typography.titleLarge)}
                Column(Modifier.weight(1f).padding(start=12.dp).clickable {onMarket(symbol)}) {
                    Text(symbol.substringBefore('/').substringBefore('_'),style=MaterialTheme.typography.titleMedium)
                    Text(if(symbol.contains("_")) if(m.optJSONObject("instrument")?.value("kind") in listOf("stock_linked_perpetual","index_linked_perpetual")) "Stock-linked · Perpetual" else "USDT · Perpetual" else "${symbol.substringAfter('/')} · Spot",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
                }
                Column(horizontalAlignment=Alignment.End,modifier=Modifier.clickable {onMarket(symbol)}) {
                    Text(price(q.value("last")),fontFamily=ZenFonts.Mono,style=MaterialTheme.typography.titleMedium)
                    Text(if(m.optBoolean("stale")) "STALE" else q.value("change_percent")?.let {number(it)+"%"} ?: "Change unavailable",color=if(m.optBoolean("stale")) ZenColors.Muted else pnlColor(q.value("change_percent")),style=MaterialTheme.typography.bodySmall)
                }
                IconButton(onClick={favorites=if(symbol in favorites) favorites-symbol else favorites+symbol;prefs.edit().putStringSet("favorites",favorites).apply()}){Icon(if(symbol in favorites) Icons.Rounded.Star else Icons.Rounded.StarBorder,contentDescription=if(symbol in favorites) "Remove $symbol from watchlist" else "Add $symbol to watchlist",tint=if(symbol in favorites) ZenColors.Blue else ZenColors.Muted,modifier=Modifier.size(20.dp))}
            }
            }
        }
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
        item {PageHeading("Positions","Open risk and protective exits.")}
        if(rows.isEmpty()) item {EmptyState("No open positions","Open positions from your active trading workspace appear here.","Explore markets",onMarkets)}
        items(rows,key={it.getString("id")}) {p->SurfaceCard {
            SectionLabel(p.getString("symbol").replace("_"," / ")) {StatusPill((p.value("side") ?: "LONG")+" · "+(p.value("product") ?: "SPOT").uppercase(),if(p.value("side")=="SHORT") ZenColors.Red else ZenColors.Emerald)}
            Text(signedMoney(p.value("unrealized")),style=MaterialTheme.typography.headlineMedium,color=pnlColor(p.value("unrealized")),fontFamily=ZenFonts.Mono)
            Text("Unrealized P&L",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
            Row(Modifier.fillMaxWidth()) {MiniMetric("Entry",price(p.value("entry")),modifier=Modifier.weight(1f));MiniMetric("Current mark",price(p.value("mark")),modifier=Modifier.weight(1f))}
            HorizontalDivider(color=ZenColors.Border)
            KeyValue("Exposure",money(p.value("notional")));if(p.value("product")=="futures"){KeyValue("Leverage / margin",(p.value("leverage") ?: "—")+"× · "+(p.value("margin_mode") ?: "—"));KeyValue("Liquidation",price(p.value("liquidation_price")))};KeyValue("Stop / take profit","${number(p.value("stop"))} / ${number(p.value("take_profit"))}")
            if(p.optBoolean("stale")) Text("Market price is stale. Closing needs a fresh quote.",color=ZenColors.Red,style=MaterialTheme.typography.bodySmall)
            PrimaryAction("Manage position",enabled=!c.loading){onPosition(p)}
        }}
    }
}
@Composable fun SettingsScreen(c: ZenController,onRisk: ()->Unit,onExchange: ()->Unit,onConfirm: (Confirmation)->Unit,share: (String)->Unit,onTrading: ()->Unit) {
    LazyColumn(Modifier.fillMaxSize(),contentPadding=PaddingValues(22.dp,16.dp,22.dp,24.dp),verticalArrangement=Arrangement.spacedBy(18.dp)) {
        item {PageHeading("Workspace","Connections, security and control.")}
        item {SurfaceCard {
            Eyebrow("Account")
            Text(c.snapshot.optJSONObject("account")?.value("email") ?: "Owner workspace",style=MaterialTheme.typography.titleMedium)
            Text("Session protected by Android Keystore. Your password is not stored.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
        }}
        item {SurfaceCard {
            SettingsRow("Trading controls","Spot, perpetuals, leverage and account activation",Icons.Rounded.CandlestickChart,onTrading)
            HorizontalDivider(color=ZenColors.Border)
            SettingsRow("Risk limits","Exposure, loss budgets and protective controls",Icons.Rounded.Shield,onRisk)
            HorizontalDivider(color=ZenColors.Border)
            SettingsRow("Exchange connections","Account access with encrypted credentials.",Icons.Rounded.Link,onExchange)
        }}
        if(c.connections.length()>0) item {SurfaceCard {
            Eyebrow("Connected exchanges")
            c.connections.rows().forEach {connection->Row(verticalAlignment=Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {Text(connection.getString("exchange").replaceFirstChar {it.uppercase()},style=MaterialTheme.typography.titleMedium);Text("Credentials encrypted on server",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}
                TextButton(onClick={onConfirm(Confirmation("Remove connection","Remove stored credentials from ZEN. Revoke the API key on the exchange separately.","Remove",true){c.removeConnection(connection.getString("id"))})}) {Text("Remove",color=ZenColors.Red)}
            }}
        }}
        item {SurfaceCard {
            SectionLabel("Trading environment") {StatusPill(c.portfolio.value("mode") ?: "PAPER")}
            Text("Paper uses simulated capital. Native MEXC futures can be separately connected and authorized. Private order acceptance has not been validated in this release.",style=MaterialTheme.typography.bodyMedium,color=ZenColors.Muted)
            KeyValue("Product",c.portfolio.value("product") ?: "spot");KeyValue("Backend",if(c.connected) "Connected" else "Disconnected");KeyValue("Observer",if(c.health.optBoolean("worker_online")) "Online" else "Offline")
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
