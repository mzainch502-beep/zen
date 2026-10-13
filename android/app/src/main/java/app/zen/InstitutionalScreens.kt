package app.zen

import androidx.compose.foundation.*
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.json.JSONObject
import java.util.UUID

@Composable fun DeskIconButton(resource:Int,label:String,tint:androidx.compose.ui.graphics.Color=ZenColors.Muted,onClick:()->Unit) {
    IconButton(onClick=onClick,modifier=Modifier.size(44.dp)){Icon(painterResource(resource),label,tint=tint,modifier=Modifier.size(20.dp))}
}
@Composable fun ExecutiveHome(c:ZenController,onCapital:()->Unit,onMarkets:()->Unit,onPortfolio:()->Unit,onAI:()->Unit) {
    val p=c.portfolio;val total=p.value("equity")
    LazyColumn(Modifier.fillMaxSize().testTag("home-scroll"),contentPadding=PaddingValues(16.dp,16.dp,16.dp,24.dp),verticalArrangement=Arrangement.spacedBy(16.dp)) {
        item {Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically){PageHeading("Overview","Personal investment workspace");DeskIconButton(R.drawable.ic_nav_settings,"Paper capital setup",onClick=onCapital)}}
        item {SurfaceCard {
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Eyebrow("Net asset value");Text(if(p.optBoolean("paper",true)) "SIMULATED" else "LIVE",style=MaterialTheme.typography.labelSmall,color=ZenColors.Gold)}
            Text(money(total),style=MaterialTheme.typography.displaySmall,fontFamily=ZenFonts.Mono)
            Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(8.dp)){Text(signedMoney(p.value("daily_net")),color=pnlColor(p.value("daily_net")),style=MaterialTheme.typography.titleMedium,fontFamily=ZenFonts.Mono);Text("daily net",color=ZenColors.Muted,style=MaterialTheme.typography.bodySmall)}
            HorizontalDivider(color=ZenColors.Border)
            Row(Modifier.fillMaxWidth()){MiniMetric("Available cash",money(p.value("cash")),modifier=Modifier.weight(1f));MiniMetric("Unrealized P&L",signedMoney(p.value("unrealized")),pnlColor(p.value("unrealized")),Modifier.weight(1f))}
            if(p.optBoolean("stale")) Text("Valuation unavailable until marks are fresh",color=ZenColors.Warning,style=MaterialTheme.typography.bodySmall)
        }}
        if(p.value("product")!="combined" && p.optBoolean("paper",true)) item {SurfaceCard {SectionLabel("Shared paper portfolio");Text("Initialize one capital amount across spot and futures. Existing positions must be closed first.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted);PrimaryAction("Initialize paper portfolio",!c.loading,onCapital)}}
        item {PerformanceChart(c)}
        item {Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(12.dp)){OutlinedButton(onClick=onPortfolio,modifier=Modifier.weight(1f)){Text("Portfolio · ${c.positions.length()}")};OutlinedButton(onClick=onMarkets,modifier=Modifier.weight(1f)){Text("Trade")}}}
        item {SurfaceCard {SectionLabel("Intelligence operations"){TextButton(onClick=onAI){Text("Inspect")}};KeyValue("Learning outcomes",c.research.optJSONObject("learning")?.value("samples") ?: "—");KeyValue("Market catalogue",c.research.value("catalogue_count") ?: "—");Text(c.research.optJSONObject("scan")?.let {"${it.optInt("evaluated")} evaluated · ${it.optInt("fills")} fills · ${it.optInt("risk_vetoes")} vetoes in the latest scan"} ?: "First scan pending",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}}
        item {Text("Income objective $80/day · aspirational, never a quota",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}
        item {SectionLabel("Activity");if(c.events.length()==0) Text("No account events yet",color=ZenColors.Muted) else c.events.rows().take(3).forEach {ActivityRow(it);Spacer(Modifier.height(12.dp))}}
    }
}
@Composable fun PerformanceChart(c:ZenController,expanded:Boolean=false) {
    var period by remember {mutableStateOf("1D")};var full by remember {mutableStateOf(false)};var selected by remember {mutableStateOf<Int?>(null)}
    LaunchedEffect(period,c.connected){if(c.connected)c.history(period)}
    val points=c.historyData.optJSONArray("points")?.rows().orEmpty()
    SurfaceCard {
        SectionLabel("Portfolio performance"){Row {DeskIconButton(R.drawable.ic_nav_performance,"Full-screen performance chart"){full=true};TextButton(onClick={c.history(period)}){Text("Refresh")}}}
        Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(6.dp)){listOf("1D","7D","30D","90D","1Y","ALL").forEach {p->FilterChip(period==p,{period=p;selected=null},label={Text(p)})}}
        if(c.historyLoading) LinearProgressIndicator(Modifier.fillMaxWidth())
        if(points.size<2) Text("Insufficient recorded snapshots. No performance curve is inferred.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
        else EquityPlot(points,if(expanded) 280 else 140,selected,{selected=it})
        selected?.let {i->points.getOrNull(i)?.let {p->Text("${java.text.SimpleDateFormat("MMM d, HH:mm",java.util.Locale.getDefault()).format(java.util.Date((p.optDouble("timestamp")*1000).toLong()))} · ${money(p.value("equity"))}",style=MaterialTheme.typography.bodySmall,fontFamily=ZenFonts.Mono)}}
        Text("Recorded simulated NAV · funding settlement unavailable",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
    }
    if(full) androidx.compose.ui.window.Dialog(onDismissRequest={full=false},properties=androidx.compose.ui.window.DialogProperties(usePlatformDefaultWidth=false)){Surface(Modifier.fillMaxSize(),color=ZenColors.Background){Column(Modifier.statusBarsPadding().navigationBarsPadding().padding(16.dp)){TextButton(onClick={full=false}){Text("Close chart")};if(points.size<2) Text("Insufficient recorded snapshots") else EquityPlot(points,360,selected,{selected=it});Text(selected?.let {money(points.getOrNull(it)?.value("equity"))} ?: "Tap to inspect a recorded valuation")}}}
}
@Composable fun EquityPlot(points:List<JSONObject>,height:Int,selected:Int?,onSelect:(Int)->Unit) {
    val values=points.mapNotNull {it.value("equity")?.toDoubleOrNull()};if(values.size!=points.size)return
    val low=values.minOrNull()!!;val high=values.maxOrNull()!!;val range=(high-low).takeIf {it>0} ?: 1.0;val accent=ZenColors.Emerald;val grid=ZenColors.Border;val muted=ZenColors.Muted
    Column {
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text(money(high.toString()),style=MaterialTheme.typography.bodySmall,color=muted);Text(money(low.toString()),style=MaterialTheme.typography.bodySmall,color=muted)}
        Canvas(Modifier.fillMaxWidth().height(height.dp).pointerInput(points){detectTapGestures {p->onSelect(((p.x/size.width)*(points.size-1)).toInt().coerceIn(0,points.lastIndex))}}) {
            repeat(4){i->val y=size.height*i/3;drawLine(grid,Offset(0f,y),Offset(size.width,y),1f)}
            val path=Path();values.forEachIndexed {i,v->val x=size.width*i/(values.size-1);val y=(size.height*(1-(v-low)/range)).toFloat();if(i==0)path.moveTo(x,y) else path.lineTo(x,y)};drawPath(path,accent,style=Stroke(width=2.dp.toPx()))
            selected?.let {i->val x=size.width*i/(values.size-1);drawLine(muted,Offset(x,0f),Offset(x,size.height),1f)}
        }
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){points.firstOrNull()?.let {Text(java.text.SimpleDateFormat("MMM d",java.util.Locale.getDefault()).format(java.util.Date((it.optDouble("timestamp")*1000).toLong())),style=MaterialTheme.typography.bodySmall,color=muted)};points.lastOrNull()?.let {Text(java.text.SimpleDateFormat("HH:mm",java.util.Locale.getDefault()).format(java.util.Date((it.optDouble("timestamp")*1000).toLong())),style=MaterialTheme.typography.bodySmall,color=muted)}}
    }
}
@Composable fun PortfolioDesk(c:ZenController,onPosition:(JSONObject)->Unit,onMarkets:()->Unit) {
    var filter by remember {mutableStateOf("All")};val rows=c.positions.rows().filter {filter=="All" || it.value("product")==filter.lowercase()}
    LazyColumn(Modifier.fillMaxSize().testTag("portfolio-scroll"),contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(16.dp)) {
        item {PageHeading("Portfolio","Valuation, allocation and open exposures")}
        item {SurfaceCard {KeyValue("Net asset value",money(c.portfolio.value("equity")));KeyValue("Gross exposure",money(c.portfolio.value("gross_exposure") ?: c.portfolio.value("exposure")));KeyValue("Net exposure",money(c.portfolio.value("net_exposure")));KeyValue("Allocated margin",money(c.portfolio.value("allocated_margin")))}}
        item {Row(horizontalArrangement=Arrangement.spacedBy(8.dp)){listOf("All","Spot","Futures").forEach {v->FilterChip(filter==v,{filter=v},label={Text(v)})}}}
        if(rows.isEmpty()) item {EmptyState("No open positions","Open positions from the selected book appear here.","Explore markets",onMarkets)}
        items(rows,key={it.getString("id")}) {p->SurfaceCard {
            SectionLabel(p.getString("symbol").replace("_"," / ")){StatusPill(p.value("side") ?: "LONG",if(p.value("side")=="SHORT") ZenColors.Red else ZenColors.Emerald)}
            Text(signedMoney(p.value("unrealized")),style=MaterialTheme.typography.headlineMedium,color=pnlColor(p.value("unrealized")),fontFamily=ZenFonts.Mono)
            KeyValue("Product",p.value("product") ?: "spot");KeyValue("Entry / mark",price(p.value("entry"))+" / "+price(p.value("mark")))
            KeyValue("Exposure",money(p.value("notional")));KeyValue("Leverage",(p.value("leverage") ?: "1")+"×")
            PrimaryAction("Manage position",!c.loading){onPosition(p)}
        }}
        val allocations=c.portfolio.optJSONArray("allocation")?.rows().orEmpty()
        if(allocations.isNotEmpty()) item {SurfaceCard {SectionLabel("Asset concentration");allocations.forEach {a->KeyValue(a.getString("asset"),money(a.value("gross_notional")))}}}
    }
}
@OptIn(ExperimentalMaterial3Api::class)
@Composable fun CapitalSheet(c:ZenController,onDismiss:()->Unit,onConfirm:(Confirmation)->Unit) {
    var amount by remember {mutableStateOf("200")};var lev by remember {mutableStateOf("5")};var automatic by remember {mutableStateOf(false)};var risk by remember {mutableStateOf(true)}
    val key=remember {UUID.randomUUID().toString()}
    ModalBottomSheet(onDismissRequest=onDismiss,sheetState=rememberModalBottomSheetState(skipPartiallyExpanded=true),containerColor=ZenColors.Surface){Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(20.dp).imePadding(),verticalArrangement=Arrangement.spacedBy(14.dp)) {
        PageHeading("Paper portfolio","One capital amount · two trading books")
        ZenField("Simulated capital · USDT",amount,{amount=it});ZenField("Paper leverage ceiling · ×",lev,{lev=it})
        Text("Supports $1–$1 billion simulated capital. Half funds spot and half futures. No real funds are deposited. Close simulated positions before resetting.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
        Row(verticalAlignment=Alignment.CenterVertically){Switch(risk,{risk=it});Spacer(Modifier.width(12.dp));Text("Automatic risk recommendations",modifier=Modifier.weight(1f))}
        Text("Risk recommendations can tighten the ceiling. A 500× ceiling is a stress setting; exchange limits, costs and liquidation checks can veto entries.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Warning)
        Row(verticalAlignment=Alignment.CenterVertically){Switch(automatic,{automatic=it});Spacer(Modifier.width(12.dp));Text("Enable automatic paper trading",modifier=Modifier.weight(1f))}
        PrimaryAction("Review paper setup",!c.loading && amount.toBigDecimalOrNull()?.let {it>=java.math.BigDecimal.ONE && it<=java.math.BigDecimal("1000000000")}==true && (lev.toIntOrNull() ?: 0) in 1..500){onConfirm(Confirmation("Initialize simulated portfolio","Reset both paper books to a total of $amount USDT, split equally. ${if(automatic) "Enable" else "Disable"} automatic entries, with a $lev× outer ceiling. Live permissions are untouched.","Initialize paper"){c.initializePortfolio(JSONObject().put("amount",amount).put("futures_fraction","0.5").put("leverage_ceiling",lev.toInt()).put("auto_risk",risk).put("automatic",automatic).put("confirmation","INITIALIZE PAPER PORTFOLIO").put("client_id",key));onDismiss()})}
        Spacer(Modifier.height(24.dp))
    }}
}

@Composable fun MoreDesk(c:ZenController,section:String,onSection:(String)->Unit,light:Boolean,onTheme:(Boolean)->Unit,onRisk:()->Unit,onExchange:()->Unit,onTrading:()->Unit,onCapital:()->Unit,onConfirm:(Confirmation)->Unit,share:(String)->Unit) {
    LaunchedEffect(section){when(section){"Risk Management"->c.loadRisk();"Market Context"->c.loadContext();"Security"->c.loadCapabilities()}}
    if(section=="Overview" || section=="More") {
        LazyColumn(Modifier.fillMaxSize().testTag("more-scroll"),contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(14.dp)) {
            item {PageHeading("Workspace","Operating controls and research tools")}
            item {SurfaceCard {Text(c.snapshot.optJSONObject("account")?.value("email") ?: "Owner account",style=MaterialTheme.typography.titleMedium);Text("Session encrypted on device · credentials stay server-side",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}}
            val destinations=listOf("Portfolio" to R.drawable.ic_nav_portfolio,"Markets" to R.drawable.ic_nav_trade,"Trading Desk" to R.drawable.ic_nav_trade,"AI Intelligence" to R.drawable.ic_nav_ai,"Strategies" to R.drawable.ic_nav_strategies,"Risk Management" to R.drawable.ic_nav_risk,"Performance Analytics" to R.drawable.ic_nav_performance,"Exchange Connections" to R.drawable.ic_nav_connections,"Activity & Reports" to R.drawable.ic_nav_reports,"Market Context" to R.drawable.ic_nav_notifications,"Settings" to R.drawable.ic_nav_settings)
            items(destinations){(label,icon)->Surface(color=ZenColors.Surface,shape=RoundedCornerShape(12.dp)){Row(Modifier.fillMaxWidth().clickable{onSection(label)}.padding(16.dp).heightIn(min=44.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(14.dp)){Icon(painterResource(icon),null,tint=ZenColors.Muted,modifier=Modifier.size(21.dp));Text(label,style=MaterialTheme.typography.titleMedium)}}}
            item {Text("ZEN © 2026 · Personal research platform",style=MaterialTheme.typography.bodySmall,color=ZenColors.Gold)}
        };return
    }
    LazyColumn(Modifier.fillMaxSize().testTag("section-scroll"),contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(16.dp)) {
        item {TextButton(onClick={onSection("More")}){Text("← Workspace")};PageHeading(section,when(section){"Risk Management"->"Independent oversight and loss boundaries";"Performance Analytics"->"Recorded valuations and net outcomes";"Market Context"->"Public publisher metadata · research only";else->"Personal workspace"})}
        when(section) {
            "Risk Management"->{
                val r=c.riskData;val p=r.optJSONObject("portfolio") ?: JSONObject();val rec=r.optJSONObject("recommendation") ?: JSONObject()
                item {SurfaceCard {SectionLabel(rec.value("stage") ?: "Risk report pending");KeyValue("Gross exposure",money(p.value("gross_exposure")));KeyValue("Net exposure",money(p.value("net_exposure")));KeyValue("Margin utilization",p.value("margin_utilization")?.toBigDecimalOrNull()?.multiply(java.math.BigDecimal(100))?.let {number(it.toPlainString())+"%"} ?: "—");TextButton(onClick={c.loadRisk()}){Text("Refresh risk report")}}}
                item {SurfaceCard {SectionLabel("Recommended limits");val l=rec.optJSONObject("effective_limits") ?: JSONObject();KeyValue("Leverage ceiling",(l.value("max_leverage") ?: "—")+"×");KeyValue("Trade loss budget",money(l.value("max_loss_trade")));KeyValue("Daily loss budget",money(l.value("max_daily_loss")));Text("These tighten configured ceilings. They cannot guarantee losses stay within estimates during gaps or outages.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted);PrimaryAction("Review outer limits",!c.loading,onRisk)}}
                val scenarios=r.optJSONArray("scenarios")?.rows().orEmpty()
                if(scenarios.isNotEmpty()) item {SurfaceCard {SectionLabel("Static stress scenarios");scenarios.forEach {s->KeyValue(number((s.value("price_shock")?.toDoubleOrNull()?.times(100)).toString())+"% move",signedMoney(s.value("linear_pnl")))};Text("Linear exposure only. Stops, liquidation, funding and gaps are excluded.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Warning)}}
                item {SurfaceCard {KeyValue("Value at Risk","Unavailable");KeyValue("Correlation","Unavailable");Text("Validated synchronized return history is required before statistical risk estimates are shown.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}}
                item {PrimaryAction("Emergency trading halt",!c.loading){onConfirm(Confirmation("Emergency trading halt","Prevent new positions. Protective exits continue; close existing exposure explicitly.","Halt entries",true){c.mode("Emergency Stop")})}}
            }
            "Performance Analytics"->{item {PerformanceChart(c,true)};item {SurfaceCard {KeyValue("Net since capital setup",signedMoney(c.portfolio.value("net_pnl")));KeyValue("Fees",money(c.portfolio.value("fees")));Text("Funding settlement and annualized risk-adjusted performance are unavailable. No returns are inferred.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}}}
            "Strategies"->{val learning=c.research.optJSONObject("learning") ?: JSONObject();item {SurfaceCard {SectionLabel("Contextual paper research");KeyValue("Version",learning.value("version") ?: "—");KeyValue("Completed samples",learning.value("samples") ?: "0");Text("Momentum, pullback and range-reversion hypotheses are ranked using observed context and bounded outcome feedback. Predictive value and live promotion are unvalidated.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}};item {PaperProfileActions(c,onConfirm)};item {PrimaryAction("Shared paper capital",!c.loading,onCapital)}}
            "Exchange Connections"->{
                item {SurfaceCard {Text("Native MEXC futures is experimental. Generic connections verify reads; universal private execution is not certified.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted);PrimaryAction("Connect or review exchange",!c.loading,onExchange);OutlinedButton(onClick=onTrading,modifier=Modifier.fillMaxWidth()){Text("Futures connection wizard")}}}
                if(c.connections.length()==0) item {EmptyState("No connected accounts","Public market data and paper trading do not need private exchange credentials.")}
                items(c.connections.rows(),key={it.getString("id")}) {cn->SurfaceCard {SectionLabel(cn.getString("exchange").replaceFirstChar {it.uppercase()});val caps=cn.optJSONObject("capabilities") ?: JSONObject();KeyValue("Product",caps.value("product") ?: "Read adapter");KeyValue("Private execution",if(caps.optBoolean("live_orders_tested")) "Verified" else "Uncertified");Text("Saved encrypted credentials are never displayed. Revocation must also be done at the exchange.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted);TextButton(onClick={onConfirm(Confirmation("Remove exchange connection","Remove the stored key from ZEN; revoke it at your exchange as well.","Remove",true){c.removeConnection(cn.getString("id"))})}){Text("Remove",color=ZenColors.Red)}}}
            }
            "Market Context"->{
                val data=c.contextData
                item {SurfaceCard {Text(data.value("notice") ?: "Loading monitored sources",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted);TextButton(onClick={c.loadContext()}){Text("Refresh context")};data.optJSONArray("sources")?.rows()?.forEach {s->KeyValue(s.value("source") ?: "Source",if(s.optJSONObject("state")?.optBoolean("available")==true) "Fetched" else "Unavailable")}}}
                val events=data.optJSONArray("events")?.rows().orEmpty()
                if(events.isEmpty()) item {EmptyState("No verified feed metadata yet","Publisher failures are recorded. ZEN does not invent headlines or assume news coverage is complete.")}
                items(events,key={it.getString("event_id")}) {e->SurfaceCard {Eyebrow(e.value("source") ?: "Source");Text(e.value("title") ?: "Headline");Text(if(e.optBoolean("review_flag")) "Requires review · not a directional trade signal" else "Research context only",style=MaterialTheme.typography.bodySmall,color=ZenColors.Warning)}}
            }
            "Activity & Reports","Alerts"->{
                if(section=="Activity & Reports") item {PrimaryAction("Export audit history",!c.loading){c.export(share)}}
                val rows=c.events.rows().filter {section!="Alerts" || (it.value("kind")?.let {k->k.contains("error") || k.contains("veto") || k.contains("disconnect")}==true)}
                if(rows.isEmpty()) item {EmptyState("No ${if(section=="Alerts") "alerts" else "events"}","Backend account events appear here as they occur.")}
                items(rows,key={it.getString("id")}) {SurfaceCard {ActivityRow(it)}}
            }
            "Account"->{item {SurfaceCard {KeyValue("Owner",c.snapshot.optJSONObject("account")?.value("email") ?: "—");Text("Email changes, public signup and password recovery are not enabled in this owner-managed release.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted);PrimaryAction("Sign out",!c.loading){onConfirm(Confirmation("Sign out","Revoke this device session. Backend trading follows its saved state and can continue; turn automation OFF first if needed.","Sign out"){c.logout()})}}}}
            "Security"->{item {SurfaceCard {KeyValue("Session storage","Android Keystore");KeyValue("Withdrawals","Not supported");KeyValue("MFA",if(c.capabilities.optBoolean("multi_factor_auth")) "Available" else "Unavailable");Text("TLS, server-side credential encryption and session revocation are implemented. MFA and secure password recovery require additional backend work.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}}}
            "Settings"->{
                item {SurfaceCard {SectionLabel("Appearance");Row(verticalAlignment=Alignment.CenterVertically){Text("Light theme",modifier=Modifier.weight(1f));Switch(light,onTheme,modifier=Modifier.testTag("theme-switch"))};Text("USDT base currency · displayed USD-equivalent estimates",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}}
                item {PrimaryAction("Paper portfolio setup",!c.loading,onCapital)}
                item {OutlinedButton(onClick=onTrading,modifier=Modifier.fillMaxWidth()){Text("Trading controls")};OutlinedButton(onClick=onRisk,modifier=Modifier.fillMaxWidth()){Text("Risk limits")}}
                item {OutlinedButton(onClick={onSection("Security")},modifier=Modifier.fillMaxWidth()){Text("Security")};OutlinedButton(onClick={onSection("Account")},modifier=Modifier.fillMaxWidth()){Text("Account")}}
                item {Text("ZEN ${BuildConfig.VERSION_NAME}\nNative Android · iOS and web release pending\nDirect stock brokers deferred",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}
            }
            else->{item {EmptyState("Screen unavailable","This capability has not been implemented or certified.")}}
        }
    }
}
