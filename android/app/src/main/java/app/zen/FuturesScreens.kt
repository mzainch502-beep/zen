package app.zen

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import org.json.JSONObject
import java.util.UUID

@OptIn(ExperimentalMaterial3Api::class)
@Composable fun FuturesSettingsSheet(c: ZenController,onDismiss: ()->Unit,onConfirm: (Confirmation)->Unit) {
    var workspace by remember {mutableStateOf(c.futures.value("workspace") ?: "spot")}
    val initial=c.futures.optJSONObject("limits") ?: JSONObject("""{"max_leverage":1,"max_margin":"3","max_notional":"40","max_loss_trade":"2","max_daily_loss":"6","max_drawdown":"20","min_liquidation_distance":"0.005","max_spread_bps":"20","max_slippage_bps":"10","max_positions":2,"max_order_rate":6,"automatic":false}""")
    val fields=listOf("max_leverage" to "Leverage ceiling · ×","max_margin" to "Margin per position · USDT","max_notional" to "Total notional · USDT","max_loss_trade" to "Maximum trade loss · USDT","max_daily_loss" to "Daily loss limit · USDT","max_drawdown" to "Maximum drawdown · USDT","min_liquidation_distance" to "Minimum liquidation distance · fraction")
    val values=remember {mutableStateMapOf<String,String>().apply {fields.forEach {(key,_)->put(key,initial.value(key).orEmpty())}}}
    var maximum by remember {mutableStateOf(c.futures.optBoolean("exchange_max"))}
    var capital by remember {mutableStateOf("")}
    var connect by remember {mutableStateOf(false)}
    var key by remember {mutableStateOf("")};var secret by remember {mutableStateOf("")};var permissions by remember {mutableStateOf(false)}
    var phrase by remember {mutableStateOf("")}
    val connections=c.connections.rows().filter {it.optJSONObject("capabilities")?.value("product")=="futures"}
    ModalBottomSheet(onDismissRequest=onDismiss,sheetState=rememberModalBottomSheetState(skipPartiallyExpanded=true),containerColor=ZenColors.Surface) {
        Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal=24.dp).imePadding(),verticalArrangement=Arrangement.spacedBy(16.dp)) {
            Eyebrow("Trading controls")
            Text("Your trading environment",style=MaterialTheme.typography.headlineMedium)
            Row(horizontalArrangement=Arrangement.spacedBy(10.dp)){FilterChip(workspace=="spot",{workspace="spot"},label={Text("Spot")});FilterChip(workspace=="futures",{workspace="futures"},label={Text("Perpetual futures")})}
            Text("Paper futures supports LONG and SHORT using real MEXC contract prices. Live orders need your credentials and a separate authorization.",color=ZenColors.Muted,style=MaterialTheme.typography.bodyMedium)
            if(workspace=="futures") {
                fields.forEach {(field,label)->ZenField(label,values[field].orEmpty(),{values[field]=it})}
                Row(verticalAlignment=Alignment.CenterVertically){Switch(maximum,{maximum=it});Spacer(Modifier.width(12.dp));Text("Use discovered maximum, within my ceiling",modifier=Modifier.weight(1f),style=MaterialTheme.typography.bodyMedium)}
                Text("The ceiling is a permission, not a guarantee. Account tiers, fees, contract minimums and liquidation distance can still veto an order.",color=ZenColors.Muted,style=MaterialTheme.typography.bodySmall)
                Text("Use the Automatic trading switch in the workspace header. Switching environments disables automation until you enable it again.",color=ZenColors.Muted,style=MaterialTheme.typography.bodySmall)
            }
            PrimaryAction("Save trading controls",enabled=!c.loading && values.values.all {it.toBigDecimalOrNull()!=null}) {
                val limits=JSONObject(initial.toString());fields.forEach {(field,_)->limits.put(field,if(field=="max_leverage") values[field]?.toIntOrNull() ?: 0 else values[field])};limits.put("automatic",c.futures.optJSONObject("limits")?.optBoolean("automatic") ?: false)
                c.saveFutures(JSONObject().put("workspace",workspace).put("limits",limits).put("exchange_max",maximum))
            }
            if(c.futures.optBoolean("activated")) OutlinedButton(onClick={onConfirm(Confirmation("Return to paper","Close and reconcile live exposure first. Keep encrypted credentials for future activation.","Return to paper"){c.deactivateFutures()})},enabled=!c.loading,modifier=Modifier.fillMaxWidth()){Text("Return to paper mode")}
            if(workspace=="futures") {
                HorizontalDivider(color=ZenColors.Border)
                SectionLabel("Paper capital")
                ZenField("Simulated balance · USDT",capital,{capital=it},"For example, 3")
                OutlinedButton(onClick={onConfirm(Confirmation("Reset simulated futures capital","This resets the simulated balance only. Close paper futures positions first. Your exchange balance is untouched.","Reset paper capital"){c.seedFutures(capital)})},enabled=!c.loading && capital.toBigDecimalOrNull()?.signum()==1,modifier=Modifier.fillMaxWidth()){Text("Reset paper capital")}
                HorizontalDivider(color=ZenColors.Border)
                SectionLabel("MEXC futures connection")
                Text("Enable account reads, order reads and futures orders on MEXC. Withdrawals and transfers must be disabled. KYC, lawful derivatives access and one-way mode are required.",color=ZenColors.Muted,style=MaterialTheme.typography.bodyMedium)
                TextButton(onClick={connect=!connect}){Text(if(connect) "Hide credential form" else "Connect MEXC futures")}
                if(connect) {
                    ZenField("Futures API key",key,{key=it},secret=true);ZenField("Futures API secret",secret,{secret=it},secret=true)
                    Row(verticalAlignment=Alignment.CenterVertically){Checkbox(permissions,{permissions=it});Text("My account permits futures; order permissions enabled, withdrawals/transfers disabled",modifier=Modifier.weight(1f),style=MaterialTheme.typography.bodySmall)}
                    PrimaryAction("Test and encrypt credentials",enabled=!c.loading && permissions && key.length>=8 && secret.length>=8){c.connectFutures(key,secret){key="";secret="";connect=false}}
                }
                if(connections.isNotEmpty()) {
                    SectionLabel("Live authorization") {StatusPill("EXPERIMENTAL",ZenColors.Red)}
                    Text("Real funds can be lost. Native private order acceptance has not been validated here. Manual orders only; automatic live strategy promotion is not established. Save automatic trials OFF before activating.",color=ZenColors.Red,style=MaterialTheme.typography.bodySmall)
                    ZenField("Type I AUTHORIZE LIVE FUTURES",phrase,{phrase=it})
                    PrimaryAction("Review live activation",enabled=!c.loading && phrase=="I AUTHORIZE LIVE FUTURES") {
                        onConfirm(Confirmation("Activate real-money futures","Authorize the encrypted MEXC connection with your saved limits. This can place real LONG/SHORT orders. There is no guaranteed return. Cross margin is not enabled in this release.","Activate live",true){c.activateFutures(connections.first().getString("id"),phrase)})
                    }
                }
            }
            c.error?.let {Text(it,color=ZenColors.Red,style=MaterialTheme.typography.bodySmall)}
            Spacer(Modifier.height(28.dp))
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable fun FuturesOrderSheet(c: ZenController,symbol: String,quote: JSONObject,onDismiss: ()->Unit,onConfirm: (Confirmation)->Unit) {
    var direction by remember {mutableStateOf("LONG")};var margin by remember {mutableStateOf("")};var leverage by remember {mutableStateOf("1")};var stop by remember {mutableStateOf("")};var take by remember {mutableStateOf("")}
    val key=remember {UUID.randomUUID().toString()};val paper=c.portfolio.optBoolean("paper",true)
    val config=c.futures.optJSONObject("limits") ?: JSONObject();val maximum=c.futures.optBoolean("exchange_max")
    val market=c.markets.rows().find {it.getJSONObject("quote").getString("symbol")==symbol};val metadata=market?.optJSONObject("contract")
    val publicMax=metadata?.optInt("maxLeverage") ?: 1
    val configuredMax=config.optInt("max_leverage",1)
    val effective=if(maximum) minOf(publicMax,configuredMax) else leverage.toIntOrNull() ?: 1
    val amount=margin.toBigDecimalOrNull();val exposure=amount?.multiply(effective.toBigDecimal())
    val valid=amount?.signum()==1 && effective>0 && stop.toBigDecimalOrNull()?.signum()==1 && take.toBigDecimalOrNull()?.signum()==1
    ModalBottomSheet(onDismissRequest=onDismiss,sheetState=rememberModalBottomSheetState(skipPartiallyExpanded=true),containerColor=ZenColors.Surface) {
        Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal=24.dp).imePadding(),verticalArrangement=Arrangement.spacedBy(16.dp)) {
            SectionLabel(symbol.replace("_"," / ")){StatusPill(if(paper) "PAPER" else "LIVE",if(paper) ZenColors.Blue else ZenColors.Red)}
            Row(horizontalArrangement=Arrangement.spacedBy(12.dp)){FilterChip(direction=="LONG",{direction="LONG"},label={Text("LONG")});FilterChip(direction=="SHORT",{direction="SHORT"},label={Text("SHORT")})}
            ZenField("Allocated margin · USDT",margin,{margin=it},"Exchange minimums apply")
            if(!maximum) ZenField("Leverage · ×",leverage,{leverage=it}) else KeyValue("Requested ceiling",effective.toString()+"× · discovered")
            KeyValue("Estimated exposure",money(exposure?.toPlainString()));KeyValue("Public contract ceiling",publicMax.toString()+"×")
            ZenField("Stop loss price",stop,{stop=it});ZenField("Take profit price",take,{take=it})
            Text("Isolated, market execution. Fees and funding reserve need additional available cash. The risk governor can reject leverage, minimum quantity or exit levels. Account-specific leverage can be lower than this public ceiling.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
            PrimaryAction(if(paper) "Review simulated futures order" else "Review real futures order",enabled=valid && !c.loading) {
                val body=JSONObject().put("symbol",symbol).put("direction",direction).put("margin",margin).put("leverage",leverage.toIntOrNull() ?: 1).put("use_exchange_max",maximum).put("stop",stop).put("take_profit",take).put("idempotency_key",key)
                onConfirm(Confirmation("Confirm $direction · ${if(paper) "paper" else "live"}","Request ${money(exposure?.toPlainString())} estimated notional using ${money(margin)} isolated margin. Final precision, fees, leverage and risk checks run on the backend. ${if(paper) "No exchange order is sent." else "Real capital is at risk; an acknowledgment is not a fill."}",if(paper) "Create paper position" else "Submit live order",!paper){c.futuresOrder(body);onDismiss()})
            }
            Spacer(Modifier.height(28.dp))
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable fun FuturesPositionSheet(c: ZenController,initial: JSONObject,onDismiss: ()->Unit,onConfirm: (Confirmation)->Unit) {
    val p=c.positions.rows().find {it.getString("id")==initial.getString("id")} ?: return
    var stop by remember {mutableStateOf(p.value("stop").orEmpty())};var take by remember {mutableStateOf(p.value("take_profit").orEmpty())};var edit by remember {mutableStateOf(false)}
    val paper=p.optBoolean("paper",true)
    fun close(fraction: String) {val key=UUID.randomUUID().toString();onConfirm(Confirmation("${if(fraction=="1") "Close" else "Reduce"} ${p.value("side")} position","Reduce ${if(fraction=="1") "100" else "50"}% using a close-only futures order. ${if(paper) "This is simulated." else "Final exchange fills may differ; unresolved submissions block duplicates."}",if(fraction=="1") "Close position" else "Reduce 50%",true){c.futuresClose(p.getString("id"),fraction,key)})}
    ModalBottomSheet(onDismissRequest=onDismiss,sheetState=rememberModalBottomSheetState(skipPartiallyExpanded=true),containerColor=ZenColors.Surface) {
        Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal=24.dp).imePadding(),verticalArrangement=Arrangement.spacedBy(16.dp)) {
            SectionLabel(p.getString("symbol").replace("_"," / ")){StatusPill((p.value("side") ?: "—")+" · "+if(paper) "PAPER" else "LIVE")}
            Text(signedMoney(p.value("unrealized")),style=MaterialTheme.typography.displaySmall,color=pnlColor(p.value("unrealized")))
            KeyValue("Contracts",number(p.value("quantity"),4));KeyValue("Margin",money(p.value("allocated_margin")));KeyValue("Leverage",(p.value("leverage") ?: "—")+"× · "+(p.value("margin_mode") ?: "—"))
            KeyValue("Entry",money(p.value("entry")));KeyValue("Mark",money(p.value("mark")));KeyValue("Liquidation",money(p.value("liquidation_price")))
            Text(p.value("liquidation_label") ?: "Liquidation unavailable",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
            KeyValue("Recorded fees",money(p.value("entry_fees")));KeyValue("Funding",p.value("funding") ?: "Not available")
            if(paper) {
                SectionLabel("Paper protective exits"){TextButton(onClick={edit=!edit}){Text(if(edit) "Hide" else "Edit")}}
                if(edit){ZenField("Stop loss",stop,{stop=it});ZenField("Take profit",take,{take=it});PrimaryAction("Save exits",enabled=!c.loading && stop.toBigDecimalOrNull()!=null && take.toBigDecimalOrNull()!=null){c.futuresExits(p.getString("id"),stop,take);edit=false}}
                else {KeyValue("Stop",money(p.value("stop")));KeyValue("Take profit",money(p.value("take_profit")))}
                Text("Paper funding settlement is not modeled. A reserve is checked at entry. Exits use real quotes and can gap.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
            } else Text("Native TP/SL was requested with new ZEN entries. Verify protection on MEXC; native protection-status reconciliation and editing are not certified here.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Red)
            OutlinedButton(onClick={close("0.5")},enabled=!c.loading,modifier=Modifier.fillMaxWidth()){Text("Reduce 50%")}
            PrimaryAction("Close position",enabled=!c.loading){close("1")}
            Spacer(Modifier.height(28.dp))
        }
    }
}
