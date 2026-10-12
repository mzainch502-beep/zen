package app.zen

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
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
    Surface(color=ZenColors.Surface.copy(alpha=.6f)) {
        Row(Modifier.fillMaxWidth().padding(horizontal=20.dp,vertical=6.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
            Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(2.dp)) {
                Text("Automatic trading",style=MaterialTheme.typography.titleMedium)
                Text(if(!known) "Loading saved state…" else if(!c.connected) "Disconnected · last known state" else if(reason!=null) reason else if(enabled) "Enabled · paper ${a.value("product") ?: "workspace"} · runs on backend" else "Disabled · observation and exits continue",style=MaterialTheme.typography.bodySmall,color=if(reason!=null) ZenColors.Blue else ZenColors.Muted)
            }
            Switch(checked=a.optBoolean("requested",enabled),enabled=known && c.connected && !c.loading && (enabled || canEnable || a.optBoolean("requested")),modifier=Modifier.testTag("automatic-trading-switch"),onCheckedChange={value->
                if(value) onConfirm(Confirmation("Enable automatic paper trading","ZEN will evaluate fresh markets and may open simulated positions within your saved limits. The research strategy is unvalidated; WAIT is allowed. No real exchange orders will be sent.","Enable"){c.automation(true)})
                else c.automation(false)
            })
        }
    }
}
