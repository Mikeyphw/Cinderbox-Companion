package com.sdvsync.mods.api

import com.sdvsync.mods.models.RemoteModFile
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class NexR2DisplayTest {
    private fun file(id: String, category: String) = RemoteModFile(
        fileId = id, fileName = "file-$id.zip", fileVersion = "1.0",
        fileSize = 2048, isPrimary = category == "MAIN", categoryName = category,
        uploadedAt = 1700000000L
    )

    @Test fun stripsExecutableAndMarkupWithoutRenderingHtml() {
        assertEquals("Hello & world", NexR2Display.text("<p>Hello &amp; world</p><script>alert('x')</script>"))
        assertFalse(NexR2Display.text("<iframe src='evil'>hidden</iframe>okay").contains("hidden"))
    }

    @Test fun malformedOrHugeMarkupIsBounded() {
        assertTrue(NexR2Display.text("<b>" + "x".repeat(50000), 120).length <= 120)
        assertEquals("", NexR2Display.text(null))
        assertEquals("", NexR2Display.text("   "))
    }

    @Test fun invalidEntitiesCannotInjectControlCodes() {
        assertEquals("A B", NexR2Display.text("A &#0; B"))
        assertEquals("☃", NexR2Display.text("&#9731;"))
    }

    @Test fun imageUrlRequiresTrustedHttpsNexusHost() {
        assertEquals("https://staticdelivery.nexusmods.com/path.jpg",
            NexR2Display.imageUrl("https://staticdelivery.nexusmods.com/path.jpg"))
        for (url in listOf("http://staticdelivery.nexusmods.com/p.jpg", "javascript:alert(1)",
                           "https://nexusmods.com.evil.org/p.png", "https://user@nexusmods.com/a",
                           "https://nexusmods.com:444/x", "data:image/png;base64,a")) {
            assertNull(url, NexR2Display.imageUrl(url))
        }
    }

    @Test fun unknownTimestampsAndBadDatesAreNotPresentedAsFact() {
        assertNull(NexR2Display.dateUtc(0))
        assertNull(NexR2Display.dateUtc(-3))
        assertNull(NexR2Display.dateUtc(Long.MAX_VALUE))
        assertEquals("2023-11-14", NexR2Display.dateUtc(1700000000L))
        assertEquals("2023-11-14", NexR2Display.dateUtc(1700000000000L))
    }

    @Test fun providerFileCategoriesPreserveUnknownAndRejectDuplicates() {
        val result = NexR2Display.groupedFiles(listOf(
            file("1", "MAIN"), file("2", "updates"), file("3", "Optional Files"),
            file("4", "OLD_VERSION"), file("5", "???"), file("1", "main")
        ))
        assertEquals(listOf(NexR2Display.FileGroup.MAIN, NexR2Display.FileGroup.UPDATES,
            NexR2Display.FileGroup.OPTIONAL, NexR2Display.FileGroup.OLD,
            NexR2Display.FileGroup.OTHER), result.map { it.kind })
        assertEquals(5, result.sumOf { it.files.size })
    }

    @Test fun noFilesOrMissingMetadataRemainUnknown() {
        assertTrue(NexR2Display.groupedFiles(emptyList()).isEmpty())
        assertEquals("Size unavailable", NexR2Display.fileSize(0))
        assertEquals("Unavailable", NexR2Display.compactCount(-1))
    }

    @Test fun fileGroupsRemainBoundedAndDeterministic() {
        val groups = NexR2Display.groupedFiles((0..300).map { file(it.toString(), "main") })
        assertEquals(120, groups.sumOf { it.files.size })
        assertEquals("0", groups.first().files.first().fileId)
    }
}
