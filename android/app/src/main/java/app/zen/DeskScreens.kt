package app.zen

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.json.JSONObject

@Composable fun PaperProfileActions(c: ZenController,onConfirm: (Confirmation)->Unit) {
    if(c.futures.optBoolean("activated")) return
    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
        listOf("aggressive","balanced").forEach {profile->
            OutlinedButton(onClick={onConfirm(Confirmation("Start $profile paper trading","Uses simulated futures capital only. ${if(profile=="aggressive") "Momentum, pullback and range trials; 5× ceiling, $3 margin, $80 total exposure." else "Selective trials; 1× ceiling, $3 margin, $40 total exposure."} Loss limits remain $2 per trade, $6 daily and $20 drawdown. This enables automation and saves the profile across sign-ins. Results are experimental.","Start paper"){c.paperProfile(profile)})},enabled=!c.loading,modifier=Modifier.weight(1f).heightIn(min=48.dp)){Text(profile.replaceFirstChar {it.uppercase()},style=MaterialTheme.typography.labelLarge)}
        }
    }
}
@Composable fun HomeScreen(c: ZenController,onMarkets: ()->Unit,onPositions: ()->Unit,onAgent: ()->Unit,onRisk: ()->Unit,onConfirm: (Confirmation)->Unit) {
    val p=c.portfolio;val r=c.research;val learning=r.optJSONObject("learning") ?: JSONObject()
    var details by remember {mutableStateOf(false)}
    LazyColumn(Modifier.fillMaxSize(),contentPadding=PaddingValues(20.dp,14.dp,20.dp,24.dp),verticalArrangement=Arrangement.spacedBy(18.dp)) {
        item {PageHeading("Overview",if(p.optBoolean("paper",true)) "Paper desk · ${(r.value("profile") ?: "balanced").replaceFirstChar {it.uppercase()}}" else "Your exchange account")}
        if(!c.futures.optBoolean("activated")) item {PaperProfileActions(c,onConfirm)}
        item {
            Eyebrow(if(p.optBoolean("paper",true)) "SIMULATED EQUITY · USDT" else "EQUITY · USDT")
            Spacer(Modifier.height(6.dp));Text(money(p.value("equity")),style=MaterialTheme.typography.displaySmall)
            Spacer(Modifier.height(8.dp));Row(horizontalArrangement=Arrangement.spacedBy(10.dp)){Text(signedMoney(p.value("daily_net")),color=pnlColor(p.value("daily_net")),style=MaterialTheme.typography.titleMedium);Text("today · after fees",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}
            if(p.optBoolean("stale")) Text("Valuation stale · awaiting fresh marks",color=ZenColors.Red,style=MaterialTheme.typography.bodySmall)
        }
        item {SurfaceCard {
            Row(Modifier.fillMaxWidth()){MiniMetric("Available",money(p.value("cash")),modifier=Modifier.weight(1f));MiniMetric("Open P&L",signedMoney(p.value("unrealized")),pnlColor(p.value("unrealized")),Modifier.weight(1f))}
            TextButton(onClick={details=!details},contentPadding=PaddingValues(0.dp)){Text(if(details) "Hide breakdown" else "Portfolio breakdown")}
            if(details){KeyValue("Net since start",signedMoney(p.value("net_pnl")));KeyValue("Fees",money(p.value("fees")));KeyValue("Funding",p.value("funding") ?: "Settlement unavailable");KeyValue("Exposure",money(p.value("exposure")))}
        }}
        item {Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(10.dp)) {
            OutlinedButton(onClick=onMarkets,modifier=Modifier.weight(1f)){Text("Markets · ${c.markets.length()}")}
            OutlinedButton(onClick=onPositions,modifier=Modifier.weight(1f)){Text("Positions · ${c.positions.length()}")}
        }}
        item {SurfaceCard {
            SectionLabel("Research activity") {TextButton(onClick=onAgent){Text("Inspect")}}
            Row(Modifier.fillMaxWidth()){MiniMetric("Catalogue",r.value("catalogue_count") ?: "—",modifier=Modifier.weight(1f));MiniMetric("Learning outcomes",learning.value("samples") ?: "—",modifier=Modifier.weight(1f))}
            Text(r.optJSONObject("scan")?.let {"Latest scan: ${it.optInt("evaluated")} evaluated · ${it.optInt("fills")} fills · ${it.optInt("risk_vetoes")} vetoes"} ?: "Waiting for the first completed scan",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
        }}
        item {SurfaceCard {SectionLabel("Risk budget"){TextButton(onClick=onRisk){Text("Edit")}};val l=if(p.value("product")=="futures") c.futures.optJSONObject("limits") ?: c.limits else c.limits;KeyValue("Daily loss limit",money(l.value("max_daily_loss")));KeyValue("Exposure ceiling",money(l.value("max_notional")))}}
        item {Text("$25 daily aspiration · never a quota",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}
        if(c.events.length()>0) item {SectionLabel("Latest event");Spacer(Modifier.height(12.dp));ActivityRow(c.events.getJSONObject(0))}
    }
}
@Composable fun AgentScreen(c: ZenController,onConfirm: (Confirmation)->Unit) {
    val r=c.research;val learning=r.optJSONObject("learning") ?: JSONObject();val mode=c.portfolio.value("mode");val paused=mode!="Paper" && mode!="Live";val live=c.futures.optBoolean("activated")
    val decisions=(r.optJSONArray("candidates")?.rows() ?: c.events.rows().filter {it.value("kind")=="decision"}.map {it.getJSONObject("payload")})
    LazyColumn(Modifier.fillMaxSize().testTag("agent-scroll"),contentPadding=PaddingValues(16.dp,12.dp,16.dp,20.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        item {PageHeading("Intelligence","Market assessment and decision evidence")}
        item {SurfaceCard {
            SectionLabel("Research desk"){StatusPill(if(paused) "PAUSED" else if(r.optBoolean("scan_stale")) "STALE SCAN" else if(c.health.optBoolean("worker_online")) "SCANNING" else "OFFLINE")}
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(12.dp)){MiniMetric("Markets",r.value("catalogue_count") ?: "—",modifier=Modifier.weight(1f));MiniMetric("Evaluations",r.value("recent_evaluations") ?: "—",modifier=Modifier.weight(1f))}
            Text("${(r.value("profile") ?: "balanced").replaceFirstChar {it.uppercase()}} research · ${if(live) "live permissions" else "paper workspace"}",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
            r.value("scan_age_seconds")?.let {KeyValue("Last scan",it+"s ago")}
            r.optJSONObject("scan")?.let {scan->Text("Last batch · ${scan.optInt("evaluated")} evaluated · ${scan.optInt("fills")} fills · ${scan.optInt("risk_vetoes")} vetoes",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}
            if(r.optBoolean("scan_stale")) Text("No recent completed scan. Check backend connectivity before expecting entries.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Warning)
            DetailDisclosure("Research profile","Select the pace of paper experiments","research-profile"){PaperProfileActions(c,onConfirm)}
            PrimaryAction(if(paused) "Resume workspace" else "Pause new positions",!c.loading){onConfirm(Confirmation(if(paused) "Resume workspace" else "Pause new positions","Protective exits continue. Resuming keeps your saved automation preference.",if(paused) "Resume" else "Pause"){if(paused && live) c.activateFutures(c.futures.getString("live_connection_id"),"I AUTHORIZE LIVE FUTURES") else c.mode(if(paused) "Paper" else "Paused")})}
        }}
        item {SectionLabel("Learning journal")}
        item {SurfaceCard {
            Text((learning.value("status") ?: "Collecting outcomes").replaceFirstChar {it.uppercase()},style=MaterialTheme.typography.titleMedium)
            Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.SpaceBetween){Text("Completed exposures",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted,modifier=Modifier.weight(1f));Text(learning.value("samples") ?: "0",style=MaterialTheme.typography.titleMedium,fontFamily=ZenFonts.Mono)}

            learning.optJSONObject("shadow")?.let {sh->Text("Forward shadow trials · ${sh.optInt("open")} active / ${sh.optInt("completed")} completed",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}
            val weights=learning.optJSONObject("weights")
            val entries=weights?.keys()?.asSequence()?.toList()?.sorted().orEmpty()
            val suspended=entries.count {weights!!.getJSONObject(it).optBoolean("suspended")}
            if(suspended>0) Text("$suspended of ${entries.size} groups need review after losses. Their entries remain withheld.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Warning)
            DetailDisclosure("Review learning evidence","${entries.size} strategy groups · model details","learning-details") {
            KeyValue("Model",learning.value("version") ?: "contextual-paper-v2")
            Text(if(learning.has("shadow")) "Suspended groups collect forward shadow trials without placing orders. Eight completed trials with a positive net result, five wins and a profit factor above 1.25 can permit paper probation. This does not validate live promotion." else "Outcomes adjust bounded preferences. Forward recovery status is unavailable from this backend.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
            entries.forEach {key->val w=weights!!.getJSONObject(key)
                Column(Modifier.fillMaxWidth().padding(vertical=6.dp),verticalArrangement=Arrangement.spacedBy(6.dp)) {
                    Text(key.substringBefore(':').replace('_',' ').replaceFirstChar {it.uppercase()}+" · "+key.substringAfter(':').replace('_',' '),style=MaterialTheme.typography.titleMedium)
                    Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.SpaceBetween) {
                        Text("${w.optInt("samples")} completed trials",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
                        Text(if(w.has("recovery_status")) (if(w.optBoolean("suspended")) "Shadow review" else "Paper probation") else if(w.optBoolean("suspended")) "Review required" else "Bias "+number(w.value("weight"),3),style=MaterialTheme.typography.bodySmall,color=if(w.optBoolean("suspended")) ZenColors.Warning else ZenColors.Muted)
                    }
                }
                if(w.has("recovery_samples")) Text("${w.optInt("recovery_samples")} / ${w.optInt("recovery_required")} forward trials",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
                HorizontalDivider(color=ZenColors.Border)
            }
            }
        }}
        val waits=r.optJSONArray("top_wait_reasons")?.rows().orEmpty()
        if(waits.isNotEmpty()) item {SurfaceCard {SectionLabel("Why entries were withheld");waits.take(3).forEach {w->Text("${w.optInt("count")} × ${w.value("reason")}",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}}}
        item {SectionLabel("Opportunity tape")}
        if(decisions.isEmpty()) item {EmptyState("First scan pending","Select a paper profile in More → Strategies. Decisions appear when fresh completed candles arrive.")}
        items(decisions.take(12),key={it.value("decision_key") ?: it.toString()}) {d->SurfaceCard {
            SectionLabel(d.value("symbol")?.replace("_"," / ") ?: "Market"){StatusPill(d.value("action") ?: "WAIT",if(d.value("action")=="SHORT") ZenColors.Red else ZenColors.Emerald)}
            Text(d.value("reason") ?: "Evaluating context",style=MaterialTheme.typography.bodyMedium)
            KeyValue("Execution",if(d.value("action")=="WAIT" && d.value("execution")=="not_requested") "No order proposed" else d.value("execution")?.replace('_',' ') ?: "Observation only")
            d.value("execution_reason")?.let {Text(it,style=MaterialTheme.typography.bodySmall,color=ZenColors.Blue)}
            DetailDisclosure("Decision evidence","Hypotheses and execution details","decision-"+(d.value("decision_key") ?: d.value("symbol") ?: "market")) {
            val ops=d.optJSONArray("opportunities")?.rows().orEmpty()
            ops.forEach {o->KeyValue((o.value("strategy") ?: "Hypothesis").replace('_',' '),"${o.value("direction")} · ${number(o.value("score"),3)}")}
            Text("Scores rank research hypotheses; they are not win probabilities.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
            }
        }}
        item {SectionLabel("Audit trail")}
        items(c.events.rows().filter {it.value("kind")!="decision"}.take(8),key={it.getString("id")}) {ActivityRow(it)}
    }
}
