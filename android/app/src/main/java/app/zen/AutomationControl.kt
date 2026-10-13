package app.zen

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.foundation.clickable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp

/** Server state is authoritative; never optimistically claim execution is on. */
@Composable fun AutomationControl(c: ZenController,onConfirm: (Confirmation)->Unit) {
    val a=c.automation
    val enabled=a.optBoolean("enabled")
    val known=a.has("enabled")
    val canEnable=a.optBoolean("can_enable")
    val reason=a.value("blocked_reason")
    var info by remember {mutableStateOf(false)}
    Surface(color=ZenColors.Header) {
        Row(Modifier.fillMaxWidth().padding(horizontal=16.dp,vertical=0.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
            Column(Modifier.weight(1f).clickable {info=true}.heightIn(min=48.dp),verticalArrangement=Arrangement.Center) {
                Text("Automatic trading",style=MaterialTheme.typography.labelLarge)
                Text(if(!known) "Loading state…" else if(!c.connected) "Disconnected · last saved state" else if(!c.health.optBoolean("worker_online")) "Observer offline · tap for details" else if(reason!=null) "Blocked · tap for details" else if(enabled) "On · backend active" else "Off · observing markets",style=MaterialTheme.typography.bodySmall,color=if(reason!=null || !c.connected) ZenColors.Warning else ZenColors.Muted)
            }
            Switch(checked=a.optBoolean("requested",enabled),enabled=known && c.connected && !c.loading && (enabled || canEnable || a.optBoolean("requested")),modifier=Modifier.testTag("automatic-trading-switch"),onCheckedChange={value->
                if(value) onConfirm(Confirmation("Enable automatic paper trading","ZEN will evaluate fresh markets and may open simulated positions within your saved limits. The research strategy is unvalidated; WAIT is allowed. No real exchange orders will be sent.","Enable"){c.automation(true)})
                else c.automation(false)
            })
        }
    }
    if(info) AlertDialog(onDismissRequest={info=false},title={Text("Automatic trading")},text={Text(reason ?: if(!known) "Waiting for saved server state." else if(!c.connected) "The backend is disconnected. The switch shows the last saved state." else if(!c.health.optBoolean("worker_online")) "The market observer is offline. The switch shows your saved automation preference; fresh market data is required for new entries." else if(enabled) "Automatic paper entries are enabled. The backend continues operating when this app closes. Strategies and risk checks can still withhold trades." else "New automatic entries are disabled. Market observation and protective exits continue.")},confirmButton={TextButton(onClick={info=false}){Text("Done")}})
}
