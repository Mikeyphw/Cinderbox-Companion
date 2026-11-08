package com.sdvsync.ui.components

import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.style.URLSpan
import android.text.method.LinkMovementMethod
import android.widget.TextView
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.text.HtmlCompat
import com.sdvsync.mods.api.NexusModPageLinks

fun markdownToHtml(md: String): String {
    var html = md
    // Headings: ## Heading → <b>Heading</b>
    html = html.replace(Regex("^#{1,6}\\s+(.+)$", RegexOption.MULTILINE)) { "<b>${it.groupValues[1]}</b>" }
    // Bold
    html = html.replace(Regex("\\*\\*(.+?)\\*\\*")) { "<b>${it.groupValues[1]}</b>" }
    // Italic
    html = html.replace(Regex("\\*(.+?)\\*")) { "<i>${it.groupValues[1]}</i>" }
    // Unordered list items: - item or * item → • item
    html = html.replace(Regex("^[-*]\\s+(.+)$", RegexOption.MULTILINE)) { "&#8226; ${it.groupValues[1]}" }
    // Newlines → <br>
    html = html.replace("\r\n", "<br>").replace("\n", "<br>")
    return html
}

val HTML_TAG_REGEX = Regex("<[a-zA-Z/]")
val BBCODE_TAG_REGEX = Regex(
    "\\[(?:b|i|u|s|url|img|size|color|font|list|quote|code|center|spoiler|line|heading)[=\\]/]",
    RegexOption.IGNORE_CASE
)

fun bbCodeToHtml(bbcode: String): String {
    var html = bbcode

    // Simple paired tags: [b]-><b>, [i]-><i>, etc.
    for (tag in listOf("b", "i", "u", "s")) {
        html = html.replace(Regex("\\[$tag]", RegexOption.IGNORE_CASE), "<$tag>")
        html = html.replace(Regex("\\[/$tag]", RegexOption.IGNORE_CASE), "</$tag>")
    }

    // [url=X]Y[/url] -> <a href="X">Y</a>
    html = html.replace(
        Regex("\\[url=([^\\]]+)](.*?)\\[/url]", setOf(RegexOption.IGNORE_CASE, RegexOption.DOT_MATCHES_ALL))
    ) {
        val safeUrl = NexusModPageLinks.safeExternalHttps(it.groupValues[1])
        if (safeUrl == null) it.groupValues[2]
        else "<a href=\"${safeUrl.replace("&", "&amp;")}\">${it.groupValues[2]}</a>"
    }

    // [url]X[/url] -> <a href="X">X</a>
    html = html.replace(
        Regex("\\[url](.*?)\\[/url]", setOf(RegexOption.IGNORE_CASE, RegexOption.DOT_MATCHES_ALL))
    ) {
        val safeUrl = NexusModPageLinks.safeExternalHttps(it.groupValues[1])
        if (safeUrl == null) it.groupValues[1]
        else "<a href=\"${safeUrl.replace("&", "&amp;")}\">${it.groupValues[1]}</a>"
    }

    // [img]X[/img] -> strip (can't render in TextView)
    html = html.replace(Regex("\\[img](.*?)\\[/img]", RegexOption.IGNORE_CASE), "")

    // [size=N] -> <big>
    html = html.replace(Regex("\\[size=[^\\]]+]", RegexOption.IGNORE_CASE), "<big>")
    html = html.replace(Regex("\\[/size]", RegexOption.IGNORE_CASE), "</big>")

    // [color=X] -> <font color="X">
    html = html.replace(Regex("\\[color=([^\\]]+)]", RegexOption.IGNORE_CASE)) {
        "<font color=\"${it.groupValues[1]}\">"
    }
    html = html.replace(Regex("\\[/color]", RegexOption.IGNORE_CASE), "</font>")

    // [font=X] -> strip (not supported in HtmlCompat)
    html = html.replace(Regex("\\[font=[^\\]]+]", RegexOption.IGNORE_CASE), "")
    html = html.replace(Regex("\\[/font]", RegexOption.IGNORE_CASE), "")

    // Lists: [list]->remove, [*]->bullet
    html = html.replace(Regex("\\[list(?:=[^\\]]*)?]", RegexOption.IGNORE_CASE), "")
    html = html.replace(Regex("\\[/list]", RegexOption.IGNORE_CASE), "")
    html = html.replace("[*]", "<br>&#8226; ")

    // [quote] -> blockquote
    html = html.replace(Regex("\\[quote(?:=[^\\]]*)?]", RegexOption.IGNORE_CASE), "<blockquote>")
    html = html.replace(Regex("\\[/quote]", RegexOption.IGNORE_CASE), "</blockquote>")

    // [code] -> monospace
    html = html.replace(Regex("\\[code]", RegexOption.IGNORE_CASE), "<tt>")
    html = html.replace(Regex("\\[/code]", RegexOption.IGNORE_CASE), "</tt>")

    // Strip unsupported tags
    for (tag in listOf("center", "spoiler", "heading")) {
        html = html.replace(Regex("\\[/?$tag]", RegexOption.IGNORE_CASE), "")
    }

    // [line] -> horizontal rule text
    html = html.replace(Regex("\\[line]", RegexOption.IGNORE_CASE), "<br>──────────<br>")

    // Newlines -> <br>
    html = html.replace("\r\n", "<br>").replace("\n", "<br>")

    return html
}

/**
 * Detects BBCode or HTML in the text and returns processed HTML string,
 * or null if the text is plain.
 */
fun toHtmlIfFormatted(text: String): String? = when {
    BBCODE_TAG_REGEX.containsMatchIn(text) -> bbCodeToHtml(text)
    HTML_TAG_REGEX.containsMatchIn(text) -> text
    else -> null
}

private val unsafeBlocks = Regex(
    """(?is)<\s*(script|style|iframe|object|embed|form|svg|video|audio)\b[^>]*>.*?<\s*/\s*\1\s*>"""
)
private val unsafeElements = Regex("""(?is)<\s*/?\s*(img|input|iframe|object|embed|meta|link)\b[^>]*>""")

/**
 * Safe rich text is rendered inside a TextView, never a browser/WebView.
 * Remove executable markup and rebuild all URLSpan objects with HTTPS validation.
 */
fun safeNexusSpanned(html: String): CharSequence {
    val bounded = html.take(32_000)
    val clean = unsafeElements.replace(unsafeBlocks.replace(bounded, " "), " ")
    val parsed = HtmlCompat.fromHtml(clean, HtmlCompat.FROM_HTML_MODE_COMPACT)
    val result = SpannableStringBuilder(parsed)
    for (span in result.getSpans(0, result.length, URLSpan::class.java)) {
        val start = result.getSpanStart(span)
        val end = result.getSpanEnd(span)
        result.removeSpan(span)
        val approved = NexusModPageLinks.safeExternalHttps(span.url)
        if (approved != null && start >= 0 && end > start) {
            result.setSpan(URLSpan(approved), start, end, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        }
    }
    return result
}

@Composable
fun HtmlText(html: String, textColor: Int, linkColor: Int, textSizeSp: Float, modifier: Modifier = Modifier) {
    AndroidView(
        modifier = modifier,
        factory = { ctx ->
            TextView(ctx).apply {
                movementMethod = LinkMovementMethod.getInstance()
                setTextColor(textColor)
                setLinkTextColor(linkColor)
                textSize = textSizeSp
            }
        },
        update = { tv ->
            tv.text = safeNexusSpanned(html)
        }
    )
}
