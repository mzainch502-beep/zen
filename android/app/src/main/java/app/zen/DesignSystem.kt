package app.zen

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.math.BigDecimal
import java.math.RoundingMode
import java.text.DecimalFormat

object ZenFonts {
    val Sans=FontFamily(Font(R.font.inter,FontWeight.Normal),Font(R.font.inter,FontWeight.SemiBold))
    val Mono=FontFamily(Font(R.font.ibm_plex_mono))
}
object ZenColors {
    var Background by mutableStateOf(Color(0xFF080D18));var Header by mutableStateOf(Color(0xFF101827))
    var Surface by mutableStateOf(Color(0xFF151F30));var Raised by mutableStateOf(Color(0xFF1C293B))
    var Border by mutableStateOf(Color(0xFF28364A));var Text by mutableStateOf(Color(0xFFF4F7FB))
    var Muted by mutableStateOf(Color(0xFF96A5B8));var Emerald by mutableStateOf(Color(0xFF00D4AA))
    var Gold by mutableStateOf(Color(0xFFC5A46D));var Positive by mutableStateOf(Color(0xFF19C58B))
    var Red by mutableStateOf(Color(0xFFF06472));var Warning by mutableStateOf(Color(0xFFF4B860));var Blue by mutableStateOf(Color(0xFF96A5B8))
    fun apply(light:Boolean) {
        Background=Color(if(light) 0xFFF4F7FB else 0xFF080D18);Header=Color(if(light) 0xFFE8EEF6 else 0xFF101827)
        Surface=Color(if(light) 0xFFFFFFFF else 0xFF151F30);Raised=Color(if(light) 0xFFEDF2F8 else 0xFF1C293B)
        Border=Color(if(light) 0xFFCAD5E2 else 0xFF28364A);Text=Color(if(light) 0xFF142238 else 0xFFF4F7FB)
        Muted=Color(if(light) 0xFF4C6078 else 0xFF96A5B8);Emerald=Color(if(light) 0xFF006D59 else 0xFF00D4AA)
        Gold=Color(if(light) 0xFF7A5B22 else 0xFFC5A46D);Positive=Color(if(light) 0xFF007D56 else 0xFF19C58B)
        Red=Color(if(light) 0xFFBA2237 else 0xFFF06472);Warning=Color(if(light) 0xFF935900 else 0xFFF4B860);Blue=Muted
    }
}
@Composable fun ZenTheme(light:Boolean=false,content: @Composable ()->Unit) {
    SideEffect {ZenColors.apply(light)}
    val scheme=if(light) lightColorScheme(primary=Color(0xFF006D59),onPrimary=Color.White,background=Color(0xFFF4F7FB),surface=Color.White,surfaceVariant=Color(0xFFEDF2F8),onSurface=Color(0xFF142238),onSurfaceVariant=Color(0xFF4C6078),outline=Color(0xFFCAD5E2),error=Color(0xFFBA2237)) else darkColorScheme(primary=ZenColors.Emerald,onPrimary=ZenColors.Background,
        background=ZenColors.Background,surface=ZenColors.Surface,surfaceVariant=ZenColors.Raised,
        onSurface=ZenColors.Text,onSurfaceVariant=ZenColors.Muted,outline=ZenColors.Border,error=ZenColors.Red)
    MaterialTheme(colorScheme=scheme,
        typography=Typography(
            displaySmall=TextStyle(fontFamily=ZenFonts.Sans,fontWeight=FontWeight.SemiBold,fontSize=34.sp,lineHeight=42.sp,letterSpacing=(-1).sp),
            headlineMedium=TextStyle(fontFamily=ZenFonts.Sans,fontWeight=FontWeight.SemiBold,fontSize=24.sp,lineHeight=30.sp,letterSpacing=(-.6).sp),
            titleLarge=TextStyle(fontFamily=ZenFonts.Sans,fontWeight=FontWeight.Medium,fontSize=22.sp,lineHeight=28.sp),
            titleMedium=TextStyle(fontFamily=ZenFonts.Sans,fontWeight=FontWeight.Medium,fontSize=16.sp,lineHeight=22.sp),
            bodyLarge=TextStyle(fontFamily=ZenFonts.Sans,fontSize=15.sp,lineHeight=22.sp),
            bodyMedium=TextStyle(fontFamily=ZenFonts.Sans,fontSize=14.sp,lineHeight=22.sp),
            bodySmall=TextStyle(fontFamily=ZenFonts.Sans,fontSize=12.sp,lineHeight=18.sp),
            labelLarge=TextStyle(fontFamily=ZenFonts.Sans,fontWeight=FontWeight.Medium,fontSize=13.sp,lineHeight=18.sp),
            labelSmall=TextStyle(fontFamily=ZenFonts.Sans,fontWeight=FontWeight.Medium,fontSize=12.sp,lineHeight=16.sp,letterSpacing=.6.sp)
        ),content=content)
}
@Composable fun SurfaceCard(modifier: Modifier=Modifier,content: @Composable ColumnScope.()->Unit) {
    Surface(modifier.fillMaxWidth(),shape=RoundedCornerShape(16.dp),color=ZenColors.Surface,border=BorderStroke(.7.dp,ZenColors.Border.copy(alpha=.7f))) {
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
    if(value.length>18 || label.length>24) Column(Modifier.fillMaxWidth(),verticalArrangement=Arrangement.spacedBy(4.dp)) {
        Text(label,style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
        Text(value,style=MaterialTheme.typography.bodyMedium,color=color,fontFamily=ZenFonts.Mono)
    } else Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(12.dp),verticalAlignment=Alignment.CenterVertically) {
        Text(label,style=MaterialTheme.typography.bodyMedium,color=ZenColors.Muted,modifier=Modifier.weight(1f))
        Text(value,style=MaterialTheme.typography.bodyMedium,color=color,fontFamily=ZenFonts.Mono,modifier=Modifier.weight(1f),textAlign=androidx.compose.ui.text.style.TextAlign.End)
    }
}
@Composable fun MiniMetric(label: String,value: String,color: Color=ZenColors.Text,modifier: Modifier=Modifier) {
    Column(modifier,verticalArrangement=Arrangement.spacedBy(7.dp)) {
        Text(label,style=MaterialTheme.typography.bodySmall,color=ZenColors.Muted)
        Text(value,style=MaterialTheme.typography.titleMedium,fontFamily=ZenFonts.Mono,color=color)
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
fun pnlColor(raw: String?): Color = if((raw?.toBigDecimalOrNull()?.signum() ?: 0)<0) ZenColors.Red else if((raw?.toBigDecimalOrNull()?.signum() ?: 0)>0) ZenColors.Positive else ZenColors.Text

@Composable fun PortfolioHero(modifier: Modifier=Modifier,content: @Composable ColumnScope.()->Unit) {
    Surface(modifier.fillMaxWidth(),shape=RoundedCornerShape(28.dp),color=Color.Transparent,border=BorderStroke(.8.dp,ZenColors.Emerald.copy(alpha=.2f))) {
        Column(Modifier.background(Brush.linearGradient(listOf(Color(0xFF18302E),Color(0xFF142127),Color(0xFF111922)))).padding(24.dp),verticalArrangement=Arrangement.spacedBy(16.dp),content=content)
    }
}

fun price(raw: String?): String {
    val v=raw?.toBigDecimalOrNull() ?: return "—"
    val d=if(v.abs()<BigDecimal("0.01")) 8 else if(v.abs()<BigDecimal.ONE) 5 else 2
    return "$"+number(raw,d)
}
