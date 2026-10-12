package app.zen

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import org.json.JSONArray
import org.json.JSONObject
import java.math.BigDecimal
import java.math.RoundingMode
import java.util.UUID

@Composable fun ZenMark(modifier: Modifier=Modifier) {
    Canvas(modifier.semantics {contentDescription="ZEN monogram"}) {
        val u=size.width/100f
        drawRoundRect(androidx.compose.ui.graphics.Brush.linearGradient(listOf(ZenColors.Emerald,androidx.compose.ui.graphics.Color(0xFF39BCA8))),cornerRadius=androidx.compose.ui.geometry.CornerRadius(28*u))
        // Two offset planes form an original, crisp Z; no exchange branding.
        val top=Path().apply {moveTo(24*u,28*u);lineTo(77*u,28*u);lineTo(45*u,61*u);lineTo(26*u,61*u);lineTo(47*u,40*u);lineTo(24*u,40*u);close()}
        val bottom=Path().apply {moveTo(73*u,72*u);lineTo(21*u,72*u);lineTo(53*u,39*u);lineTo(73*u,39*u);lineTo(51*u,60*u);lineTo(73*u,60*u);close()}
        drawPath(top,ZenColors.Background);drawPath(bottom,ZenColors.Background.copy(alpha=.92f))
    }
}
@Composable fun MarketDetail(c: ZenController,symbol: String,onBack: ()->Unit,onConfirm: (Confirmation)->Unit) {
    val quote=c.markets.rows().find {it.getJSONObject("quote").getString("symbol")==symbol}?.getJSONObject("quote")
    var orderDialog by remember(symbol) {mutableStateOf(false)}
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal=22.dp,vertical=12.dp),verticalArrangement=Arrangement.spacedBy(18.dp)) {
        Row(verticalAlignment=Alignment.CenterVertically) {
            IconButton(onClick=onBack){Icon(Icons.Rounded.ArrowBack,"Back to markets")}
            Column(Modifier.weight(1f)){Text(symbol,style=MaterialTheme.typography.titleLarge);Text("${if(symbol.contains("_")) "Perpetual" else "Spot"} · ${quote?.value("source") ?: "Awaiting source"}",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}
            StatusPill(c.portfolio.value("mode") ?: "PAPER")
        }
        Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.SpaceBetween) {
            Text(money(quote?.value("last")),style=MaterialTheme.typography.headlineMedium,fontFamily=FontFamily.Monospace)
            Text(quote?.value("change_percent")?.let {number(it)+"% · 24h"} ?: "24h change unavailable",style=MaterialTheme.typography.bodySmall,color=pnlColor(quote?.value("change_percent")))
        }
        SurfaceCard {
            Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(6.dp)) {
                (if(symbol.contains("_")) listOf("1m","5m","15m","30m","1h","4h","1d") else listOf("1m","3m","5m","15m","30m","1h","4h","1d")).forEach {tf->FilterChip(c.chartTimeframe==tf,{c.chart(symbol,tf)},label={Text(tf.uppercase())})}
            }
            if(c.chartLoading) LinearProgressIndicator(Modifier.fillMaxWidth())
            if(c.candles.length()>0) CandleChart(c.candles,symbol)
            else if(!c.chartLoading) Text(c.chartError ?: "No candles received.",style=MaterialTheme.typography.bodyMedium,color=ZenColors.Muted)
            c.chartError?.let {Text(it,style=MaterialTheme.typography.bodySmall,color=ZenColors.Red);TextButton(onClick={c.chart(symbol,c.chartTimeframe)}){Text("Retry market data")}}
        }
        SurfaceCard {
            SectionLabel("Execution conditions")
            KeyValue("Bid",money(quote?.value("bid")));KeyValue("Ask",money(quote?.value("ask")))
            val bid=quote?.value("bid")?.toDoubleOrNull();val ask=quote?.value("ask")?.toDoubleOrNull();val last=quote?.value("last")?.toDoubleOrNull()
            KeyValue("Spread",if(bid!=null && ask!=null && last!=null && last>0) number(((ask-bid)/last*10000).toString())+" bps" else "—")
            KeyValue("Funding",if(symbol.contains("_")) c.markets.rows().find {it.getJSONObject("quote").getString("symbol")==symbol}?.optJSONObject("ticker")?.value("fundingRate") ?: "Unavailable" else "Not applicable · spot")
            Text("Paper fills include a conservative cost model. They do not represent exchange execution speed or personal fee tiers.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
        }
        if(c.depth.optJSONArray("bids")!=null) SurfaceCard {
            SectionLabel("Order book · top levels")
            val bids=c.depth.getJSONArray("bids");val asks=c.depth.getJSONArray("asks")
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Eyebrow("Bid price / quantity");Eyebrow("Ask price / quantity")}
            repeat(minOf(5,bids.length(),asks.length())) {i->
                val b=bids.getJSONArray(i);val a=asks.getJSONArray(i)
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                    Text("${number(b.get(0).toString())}  ${number(b.get(1).toString(),4)}",color=ZenColors.Emerald,style=MaterialTheme.typography.bodySmall,fontFamily=FontFamily.Monospace)
                    Text("${number(a.get(0).toString())}  ${number(a.get(1).toString(),4)}",color=ZenColors.Red,style=MaterialTheme.typography.bodySmall,fontFamily=FontFamily.Monospace)
                }
            }
            Text("Snapshot from ${c.depth.value("source") ?: "exchange"}; not a private order stream.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
        }
        PrimaryAction(if(symbol.contains("_")) "Open futures order" else "Create paper order",enabled=quote!=null && !c.loading) {orderDialog=true}
        Text("New exposure follows your risk limits. The daily target never overrides risk approval.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
        Spacer(Modifier.height(16.dp))
    }
    if(orderDialog && quote!=null) {if(symbol.contains("_")) FuturesOrderSheet(c,symbol,quote,onDismiss={orderDialog=false},onConfirm=onConfirm) else PaperOrderSheet(c,symbol,quote,onDismiss={orderDialog=false},onConfirm=onConfirm)}
}
@Composable fun CandleChart(rows: JSONArray,symbol: String) {
    val data=(0 until rows.length()).toList().takeLast(60).map {rows.getJSONArray(it)}
    if(data.isEmpty()) return
    var selected by remember(rows) {mutableStateOf(data.lastIndex)}
    val bar=data[selected.coerceIn(data.indices)]
    val low=data.minOf {it.getDouble(3)};val high=data.maxOf {it.getDouble(2)};val span=(high-low).coerceAtLeast(.000001)
    Column(verticalArrangement=Arrangement.spacedBy(10.dp)) {
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
            Text("O ${number(bar.get(1).toString())}   C ${number(bar.get(4).toString())}",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted,fontFamily=FontFamily.Monospace)
            Text(java.text.SimpleDateFormat("MM/dd HH:mm",java.util.Locale.getDefault()).format(java.util.Date(bar.getLong(0))),style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
        }
        Row {
            Canvas(Modifier.weight(1f).height(220.dp).semantics {contentDescription="$symbol candlestick chart, ${data.size} real candles; tap to inspect"}.pointerInput(rows) {detectTapGestures {point->selected=(point.x/size.width*data.size).toInt().coerceIn(data.indices)}}) {
                val step=size.width/data.size
                fun y(price: Double)=((high-price)/span*size.height).toFloat()
                repeat(4) {i->val level=size.height*i/3;drawLine(ZenColors.Border.copy(alpha=.5f),Offset(0f,level),Offset(size.width,level),.5f)}
                data.forEachIndexed {i,r->
                    val open=r.getDouble(1);val close=r.getDouble(4);val color=if(close>=open) ZenColors.Emerald else ZenColors.Red;val x=(i+.5f)*step
                    drawLine(color,Offset(x,y(r.getDouble(2))),Offset(x,y(r.getDouble(3))),1f)
                    drawRect(color,Offset(x-step*.29f,minOf(y(open),y(close))),Size(step*.58f,kotlin.math.abs(y(open)-y(close)).coerceAtLeast(1f)))
                }
                val x=(selected+.5f)*step
                drawLine(ZenColors.Blue.copy(alpha=.7f),Offset(x,0f),Offset(x,size.height),.7f)
            }
            Column(Modifier.height(220.dp).padding(start=9.dp),verticalArrangement=Arrangement.SpaceBetween) {
                listOf(high,low+(high-low)/2,low).forEach {Text(number(it.toString()),style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)}
            }
        }
        Text("Volume ${number(bar.get(5).toString(),2)} · Tap candles to inspect",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
    }
}
@OptIn(ExperimentalMaterial3Api::class)
@Composable fun PaperOrderSheet(c: ZenController,symbol: String,quote: JSONObject,onDismiss: ()->Unit,onConfirm: (Confirmation)->Unit) {
    var dollars by remember {mutableStateOf("")};var stop by remember {mutableStateOf("")};var take by remember {mutableStateOf("")}
    val key=remember {UUID.randomUUID().toString()}
    val price=quote.value("ask")?.toBigDecimalOrNull()
    val value=dollars.toBigDecimalOrNull()
    val qty=if(price!=null && price.signum()>0 && value!=null) value.divide(price,8,RoundingMode.DOWN) else null
    val valid=qty!=null && qty.signum()>0 && stop.toBigDecimalOrNull()?.signum()==1 && (take.isBlank() || take.toBigDecimalOrNull()?.signum()==1)
    ModalBottomSheet(onDismissRequest=onDismiss,containerColor=ZenColors.Surface,shape=RoundedCornerShape(topStart=24.dp,topEnd=24.dp)) {
        Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal=24.dp).imePadding(),verticalArrangement=Arrangement.spacedBy(16.dp)) {
            SectionLabel("Paper order") {StatusPill("LONG · SPOT")}
            Text(symbol,style=MaterialTheme.typography.headlineMedium)
            Text("Enter your own entry size and exit plan. ZEN checks risk before creating simulated exposure.",color=ZenColors.Muted)
            ZenField("Order value · USDT",dollars,{dollars=it},"Minimum 5 USDT")
            ZenField("Stop price · USDT",stop,{stop=it})
            ZenField("Take profit · optional",take,{take=it})
            KeyValue("Reference ask",money(price?.toPlainString()));KeyValue("Estimated quantity",qty?.stripTrailingZeros()?.toPlainString() ?: "—")
            KeyValue("Estimated entry fee",qty?.let {money(it.multiply(price).multiply(BigDecimal("0.001")).toPlainString())} ?: "—")
            PrimaryAction("Review paper order",enabled=valid && !c.loading) {
                val body=JSONObject().put("symbol",symbol).put("side","buy").put("quantity",qty!!.toPlainString()).put("stop",stop).put("take_profit",if(take.isBlank()) JSONObject.NULL else take).put("idempotency_key",key)
                onConfirm(Confirmation("Confirm paper order","Buy ${qty.stripTrailingZeros().toPlainString()} ${symbol.substringBefore('/')} using simulated capital. Prices may move before risk approval. No real-money order will be sent.","Create paper order") {c.order(body);onDismiss()})
            }
            Spacer(Modifier.height(24.dp))
        }
    }
}
@OptIn(ExperimentalMaterial3Api::class)
@Composable fun PositionSheet(c: ZenController,initial: JSONObject,onDismiss: ()->Unit,onConfirm: (Confirmation)->Unit) {
    if(initial.value("product")=="futures") {FuturesPositionSheet(c,initial,onDismiss,onConfirm);return}
    val id=initial.getString("id")
    val p=c.positions.rows().find {it.getString("id")==id}
    LaunchedEffect(p) {if(p==null) onDismiss()}
    if(p==null) return
    var stop by remember(id) {mutableStateOf(p.value("stop").orEmpty())};var take by remember(id) {mutableStateOf(p.value("take_profit").orEmpty())}
    var editing by remember {mutableStateOf(false)}
    fun reduction(fraction: String) {
        val qty=p.getString("quantity").toBigDecimal().multiply(fraction.toBigDecimal()).setScale(12,RoundingMode.DOWN)
        val body=JSONObject().put("symbol",p.getString("symbol")).put("side","sell").put("quantity",qty.toPlainString()).put("reduce_only",true).put("idempotency_key",UUID.randomUUID().toString())
        onConfirm(Confirmation(if(fraction=="1") "Close position" else "Reduce position","Sell ${qty.stripTrailingZeros().toPlainString()} ${p.getString("symbol").substringBefore('/')} from this paper position. The exit cannot increase exposure.",if(fraction=="1") "Close position" else "Reduce",fraction=="1") {c.order(body)})
    }
    ModalBottomSheet(onDismissRequest=onDismiss,containerColor=ZenColors.Surface) {
        Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal=24.dp).imePadding(),verticalArrangement=Arrangement.spacedBy(16.dp)) {
            SectionLabel(p.getString("symbol")) {StatusPill("LONG · PAPER")}
            Text(signedMoney(p.value("unrealized")),style=MaterialTheme.typography.headlineMedium,color=pnlColor(p.value("unrealized")))
            KeyValue("Position quantity",p.getString("quantity").toBigDecimal().stripTrailingZeros().toPlainString())
            KeyValue("Entry",money(p.value("entry")));KeyValue("Current mark",money(p.value("mark")));KeyValue("Exposure",money(p.value("notional")))
            KeyValue("Entry fees",money(p.value("entry_fees")));KeyValue("Funding","Not applicable · spot");KeyValue("Liquidation","Not applicable · spot")
            HorizontalDivider(color=ZenColors.Border)
            SectionLabel("Protective exits") {TextButton(onClick={editing=!editing}){Text(if(editing) "Hide" else "Edit")}}
            if(editing) {
                ZenField("Stop price",stop,{stop=it});ZenField("Take profit · optional",take,{take=it})
                PrimaryAction("Save protective exits",enabled=!c.loading && stop.toBigDecimalOrNull()?.signum()==1) {c.exits(id,stop,take);editing=false}
            } else {KeyValue("Stop loss",money(p.value("stop")));KeyValue("Take profit",money(p.value("take_profit")))}
            Text("Paper exits are monitored by the backend. Disconnection or gaps can delay the exit or exceed its planned loss.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
            Row(horizontalArrangement=Arrangement.spacedBy(10.dp)) {
                OutlinedButton(onClick={reduction("0.25")},enabled=!c.loading,modifier=Modifier.weight(1f),shape=RoundedCornerShape(12.dp)){Text("Reduce 25%")}
                OutlinedButton(onClick={reduction("0.5")},enabled=!c.loading,modifier=Modifier.weight(1f),shape=RoundedCornerShape(12.dp)){Text("Reduce 50%")}
            }
            OutlinedButton(onClick={reduction("1")},enabled=!c.loading,modifier=Modifier.fillMaxWidth().heightIn(min=48.dp),shape=RoundedCornerShape(13.dp),colors=ButtonDefaults.outlinedButtonColors(contentColor=ZenColors.Red)){Text("Close position")}
            Spacer(Modifier.height(24.dp))
        }
    }
}
@OptIn(ExperimentalMaterial3Api::class)
@Composable fun RiskSheet(c: ZenController,onDismiss: ()->Unit) {
    val fields=listOf("max_loss_trade" to "Loss per trade · USDT","max_daily_loss" to "Daily loss limit · USDT","max_notional" to "Total exposure · USDT","max_drawdown" to "Maximum drawdown · USDT","max_positions" to "Simultaneous positions","max_spread_bps" to "Maximum spread · bps","max_slippage_bps" to "Modeled slippage · bps","max_order_rate" to "Orders per minute","cooldown_seconds" to "Loss cooldown · seconds")
    val values=remember {mutableStateMapOf<String,String>().apply {fields.forEach {(key,_)->put(key,c.limits.value(key).orEmpty())}}}
    ModalBottomSheet(onDismissRequest=onDismiss,containerColor=ZenColors.Surface) {
        Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal=24.dp).imePadding(),verticalArrangement=Arrangement.spacedBy(14.dp)) {
            Text("Risk limits",style=MaterialTheme.typography.headlineMedium)
            Text("Hard constraints for new exposure. Closing positions remains available when trading is paused.",style=MaterialTheme.typography.bodyMedium,color=ZenColors.Muted)
            fields.forEach {(key,label)->ZenField(label,values[key].orEmpty(),{values[key]=it})}
            KeyValue("Leverage","1× · spot only")
            PrimaryAction("Save risk limits",enabled=!c.loading && values.values.all {it.toBigDecimalOrNull()!=null}) {
                val body=JSONObject(c.limits.toString());fields.forEach {(key,_)->body.put(key,if(key in listOf("max_positions","max_order_rate","cooldown_seconds")) values[key]?.toIntOrNull() ?: 0 else values[key])}
                body.put("max_correlated_notional",values["max_notional"]);c.saveRisk(body);onDismiss()
            }
            Spacer(Modifier.height(24.dp))
        }
    }
}
@OptIn(ExperimentalMaterial3Api::class)
@Composable fun ExchangeSheet(c: ZenController,onDismiss: ()->Unit) {
    var stage by remember {mutableStateOf(0)};var exchange by remember {mutableStateOf("bitget")};var key by remember {mutableStateOf("")};var secret by remember {mutableStateOf("")};var passphrase by remember {mutableStateOf("")};var readOnly by remember {mutableStateOf(false)}
    ModalBottomSheet(onDismissRequest=onDismiss,containerColor=ZenColors.Surface) {
        Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal=24.dp).imePadding(),verticalArrangement=Arrangement.spacedBy(16.dp)) {
            Eyebrow("Connection setup · ${stage+1} of 2")
            Text(if(stage==0) "Choose your exchange" else "Secure API connection",style=MaterialTheme.typography.headlineMedium)
            if(stage==0) {
                Text("Paper market data works without a private key. A read-only key lets ZEN check your exchange balances and available products.",style=MaterialTheme.typography.bodyMedium,color=ZenColors.Muted)
                listOf("bitget","binance","bybit","okx","kraken","coinbase","kucoin","gate","mexc").forEach {id->
                    Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {RadioButton(exchange==id,{exchange=id});Text(id.replaceFirstChar {it.uppercase()},style=MaterialTheme.typography.bodyLarge)}
                }
                PrimaryAction("Continue") {stage=1}
            } else {
                Text(exchange.replaceFirstChar {it.uppercase()},style=MaterialTheme.typography.titleMedium)
                Text("Required permission: read account balances. Disable trading, transfers and withdrawals on the exchange. ZEN never requests withdrawal access.",style=MaterialTheme.typography.bodyMedium,color=ZenColors.Muted)
                ZenField("API key",key,{key=it},secret=true);ZenField("API secret",secret,{secret=it},secret=true)
                if(exchange in listOf("okx","bitget","kucoin","coinbase")) ZenField("Passphrase · if required",passphrase,{passphrase=it},secret=true)
                Row(verticalAlignment=Alignment.CenterVertically) {Checkbox(readOnly,{readOnly=it});Text("Trading and withdrawals are disabled",style=MaterialTheme.typography.bodyMedium,modifier=Modifier.weight(1f))}
                Text("Your key is encrypted on the server and never returned to this app. Available capabilities depend on your account and region.",style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
                if(c.loading) LinearProgressIndicator(Modifier.fillMaxWidth())
                c.error?.let {Text(it,color=ZenColors.Red,style=MaterialTheme.typography.bodySmall)}
                PrimaryAction("Test and save connection",enabled=!c.loading && readOnly && key.length>=8 && secret.length>=8) {c.connect(exchange,key,secret,passphrase){key="";secret="";passphrase="";onDismiss()}}
                TextButton(onClick={stage=0}){Text("Choose another exchange")}
            }
            Spacer(Modifier.height(24.dp))
        }
    }
}
