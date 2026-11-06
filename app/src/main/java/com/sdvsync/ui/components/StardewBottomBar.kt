package com.sdvsync.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import com.sdvsync.R
import com.sdvsync.ui.theme.CinderboxDarkTokens as Dark

/** Stable route keys; these are the five approved dark bottom tabs in fixed order. */
enum class BottomTab(val route: String, val labelRes: Int, val testTag: String) {
    HOME("home", R.string.tab_home, "cinderbox.nav.home"),
    DOWNLOAD("game_download", R.string.tab_game, "cinderbox.nav.game"),
    SAVES("saves", R.string.tab_saves, "cinderbox.nav.saves"),
    MODS("mods", R.string.tab_mods, "cinderbox.nav.mods"),
    SETTINGS("settings", R.string.tab_more, "cinderbox.nav.more")
}

@Composable
fun StardewBottomBar(selectedTab: BottomTab, onTabSelected: (BottomTab) -> Unit, modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier.fillMaxWidth().testTag("cinderbox.shell.bottomnav")
            .drawBehind { drawLine(Dark.Line, Offset(0f, 0f), Offset(size.width, 0f), strokeWidth = 1.dp.toPx()) },
        color = Dark.Paper
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(top = 7.dp)
                .navigationBarsPadding().selectableGroup(),
            horizontalArrangement = Arrangement.SpaceEvenly
        ) {
            BottomTab.entries.forEach { tab ->
                val selected = tab == selectedTab
                val tint = if (selected) Dark.Forest else Dark.Muted
                Column(
                    modifier = Modifier.weight(1f).heightIn(min = 56.dp).testTag(tab.testTag)
                        .selectable(selected = selected, role = Role.Tab, onClick = { onTabSelected(tab) })
                        .padding(vertical = 3.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(3.dp)
                ) {
                    Surface(color = if (selected) Dark.Mint else Color.Transparent,
                        shape = RoundedCornerShape(12.dp)) {
                        ApprovedTabIcon(tab, tint, Modifier.padding(horizontal = 12.dp, vertical = 6.dp))
                    }
                    Text(stringResource(tab.labelRes),
                        style = MaterialTheme.typography.labelSmall,
                        color = tint)
                }
            }
        }
    }
}

/** Thin monoline shapes replace obsolete pixel/dither bottom tab icons. */
@Composable
private fun ApprovedTabIcon(tab: BottomTab, tint: Color, modifier: Modifier = Modifier) {
    Canvas(modifier.size(20.dp)) {
        val w = size.width
        val h = size.height
        val stroke = Stroke(width = 1.8.dp.toPx())
        when (tab) {
            BottomTab.HOME -> {
                val roof = Path().apply {
                    moveTo(w * .14f, h * .44f); lineTo(w * .50f, h * .14f)
                    lineTo(w * .86f, h * .44f);lineTo(w * .86f, h * .86f)
                    lineTo(w * .14f, h * .86f);close()
                }
                drawPath(roof, tint, style = stroke)
                drawRect(tint, Offset(w * .41f, h * .58f), Size(w * .18f, h * .28f), style = stroke)
            }
            BottomTab.DOWNLOAD -> {
                drawRoundRect(tint, topLeft = Offset(w * .08f, h * .27f),
                    size = Size(w * .84f, h * .49f),
                    cornerRadius = androidx.compose.ui.geometry.CornerRadius(5.dp.toPx()), style = stroke)
                drawLine(tint, Offset(w * .24f, h * .51f), Offset(w * .44f, h * .51f), stroke.width)
                drawLine(tint, Offset(w * .34f, h * .41f), Offset(w * .34f, h * .61f), stroke.width)
                drawCircle(tint, w * .045f, Offset(w * .69f, h * .45f))
                drawCircle(tint, w * .045f, Offset(w * .78f, h * .56f))
            }
            BottomTab.SAVES -> {
                drawRoundRect(tint, Offset(w * .20f, h * .12f), Size(w * .60f, h * .76f),
                    cornerRadius = androidx.compose.ui.geometry.CornerRadius(2.dp.toPx()), style = stroke)
                drawRect(tint, Offset(w * .32f, h * .15f), Size(w * .35f, h * .23f), style = stroke)
                drawRect(tint, Offset(w * .33f, h * .57f), Size(w * .34f, h * .27f), style = stroke)
            }
            BottomTab.MODS -> {
                val s = w * .27f
                listOf(.12f to .12f, .61f to .12f, .12f to .61f, .61f to .61f).forEach { (x,y) ->
                    drawRect(tint, Offset(w * x, h * y), Size(s,s), style = stroke)
                }
            }
            BottomTab.SETTINGS -> {
                drawCircle(tint, w * .17f, Offset(w * .5f, h * .5f), style = stroke)
                for (i in 0 until 8) {
                    val a = i * Math.PI / 4.0
                    val sx = kotlin.math.cos(a).toFloat(); val sy = kotlin.math.sin(a).toFloat()
                    drawLine(tint,
                        Offset(w * (.5f + sx * .31f), h * (.5f + sy * .31f)),
                        Offset(w * (.5f + sx * .44f), h * (.5f + sy * .44f)), stroke.width)
                }
            }
        }
    }
}
