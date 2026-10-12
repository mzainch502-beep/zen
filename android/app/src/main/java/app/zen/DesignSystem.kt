package app.zen

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.math.BigDecimal
import java.math.RoundingMode
import java.text.DecimalFormat

object ZenColors {
    val Background=Color(0xFF080B10)
    val Surface=Color(0xFF10161F)
    val Raised=Color(0xFF1B2532)
    val Border=Color(0xFF263446)
    val Text=Color(0xFFF2F5F7)
    val Muted=Color(0xFF8F9CAE)
    val Emerald=Color(0xFF78E7C4)
    val Red=Color(0xFFEB8D98)
    val Blue=Color(0xFF96B9F3)
}
@Composable fun ZenTheme(content: @Composable ()->Unit) {
    MaterialTheme(colorScheme=darkColorScheme(primary=ZenColors.Emerald,onPrimary=ZenColors.Background,
        background=ZenColors.Background,surface=ZenColors.Surface,surfaceVariant=ZenColors.Raised,
        onSurface=ZenColors.Text,onSurfaceVariant=ZenColors.Muted,outline=ZenColors.Border,error=ZenColors.Red),
        typography=Typography(
            displaySmall=TextStyle(fontFamily=FontFamily.SansSerif,fontWeight=FontWeight.Medium,fontSize=44.sp,lineHeight=50.sp,letterSpacing=(-1).sp),
            headlineMedium=TextStyle(fontWeight=FontWeight.SemiBold,fontSize=28.sp,lineHeight=34.sp,letterSpacing=(-.6).sp),
            titleLarge=TextStyle(fontWeight=FontWeight.Medium,fontSize=22.sp,lineHeight=28.sp),
            titleMedium=TextStyle(fontWeight=FontWeight.Medium,fontSize=16.sp,lineHeight=22.sp),
            bodyLarge=TextStyle(fontSize=15.sp,lineHeight=22.sp),
            bodyMedium=TextStyle(fontSize=14.sp,lineHeight=22.sp),
            bodySmall=TextStyle(fontSize=12.sp,lineHeight=18.sp),
            labelLarge=TextStyle(fontWeight=FontWeight.Medium,fontSize=13.sp,lineHeight=18.sp),
            labelSmall=TextStyle(fontWeight=FontWeight.Medium,fontSize=11.sp,lineHeight=16.sp,letterSpacing=.6.sp)
        ),content=content)
}
@Composable fun SurfaceCard(modifier: Modifier=Modifier,content: @Composable ColumnScope.()->Unit) {
    Surface(modifier.fillMaxWidth(),shape=RoundedCornerShape(24.dp),color=ZenColors.Surface,border=BorderStroke(.7.dp,ZenColors.Border.copy(alpha=.7f))) {
        Column(Modifier.padding(18.dp),verticalArrangement=Arrangement.spacedBy(12.dp),content=content)
    }
}
@Composable fun SectionLabel(title: String,trailing: @Composable (() -> Unit)?=null) {
    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically) {
        Text(title,style=MaterialTheme.typography.titleMedium)
        trailing?.invoke()
    }
}
@Composable fun Eyebrow(text: String) {Text(text.uppercase(),style=MaterialTheme.typography.labelSmall,color=ZenColors.Muted)}
@Composable fun StatusPill(text: String,color: Color=ZenColors.Blue) {
    Row(Modifier.background(color.copy(alpha=.1f),RoundedCornerShape(50)).padding(horizontal=10.dp,vertical=6.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(6.dp)) {
        Box(Modifier.size(5.dp).background(color,RoundedCornerShape(50)))
        Text(text,style=MaterialTheme.typography.labelSmall,color=color)
    }
}
@Composable fun KeyValue(label: String,value: String,color: Color=ZenColors.Text) {
    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically) {
        Text(label,style=MaterialTheme.typography.bodyMedium,color=ZenColors.Muted,modifier=Modifier.weight(1f))
        Text(value,style=MaterialTheme.typography.bodyMedium,color=color,fontFamily=FontFamily.Monospace)
    }
}
@Composable fun MiniMetric(label: String,value: String,color: Color=ZenColors.Text,modifier: Modifier=Modifier) {
    Column(modifier,verticalArrangement=Arrangement.spacedBy(7.dp)) {
        Text(label,style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
        Text(value,style=MaterialTheme.typography.titleMedium,fontFamily=FontFamily.Monospace,color=color)
    }
}
@Composable fun EmptyState(title: String,description: String,action: String?=null,onAction: ()->Unit={}) {
    SurfaceCard {
        Text(title,style=MaterialTheme.typography.titleMedium)
        Text(description,style=MaterialTheme.typography.bodyMedium,color=ZenColors.Muted)
        if(action!=null) OutlinedButton(onClick=onAction,shape=RoundedCornerShape(12.dp)) {Text(action)}
    }
}
@Composable fun PrimaryAction(label: String,enabled: Boolean=true,onClick: ()->Unit) {
    Button(onClick=onClick,enabled=enabled,modifier=Modifier.fillMaxWidth().heightIn(min=50.dp),shape=RoundedCornerShape(18.dp)) {Text(label)}
}
fun number(raw: String?,decimals: Int=2): String {
    val value=raw?.toBigDecimalOrNull() ?: return "—"
    val formatter=DecimalFormat(if(decimals==0) "#,##0" else "#,##0."+"0".repeat(decimals))
    formatter.roundingMode=RoundingMode.HALF_UP
    return formatter.format(value)
}
fun money(raw: String?): String = if(raw?.toBigDecimalOrNull()==null) "—" else "$"+number(raw)
fun signedMoney(raw: String?): String {
    val value=raw?.toBigDecimalOrNull() ?: return "—"
    return (if(value.signum()>0) "+" else if(value.signum()<0) "−" else "")+"$"+number(value.abs().toPlainString())
}
fun pnlColor(raw: String?): Color = if((raw?.toBigDecimalOrNull()?.signum() ?: 0)<0) ZenColors.Red else if((raw?.toBigDecimalOrNull()?.signum() ?: 0)>0) ZenColors.Emerald else ZenColors.Text

@Composable fun PortfolioHero(modifier: Modifier=Modifier,content: @Composable ColumnScope.()->Unit) {
    Surface(modifier.fillMaxWidth(),shape=RoundedCornerShape(28.dp),color=Color.Transparent,border=BorderStroke(.8.dp,ZenColors.Emerald.copy(alpha=.2f))) {
        Column(Modifier.background(Brush.linearGradient(listOf(Color(0xFF18302E),Color(0xFF142127),Color(0xFF111922)))).padding(24.dp),verticalArrangement=Arrangement.spacedBy(16.dp),content=content)
    }
}
