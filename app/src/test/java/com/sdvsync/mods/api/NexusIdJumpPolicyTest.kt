package com.sdvsync.mods.api

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class NexusIdJumpPolicyTest {
    @Test fun validDirectIdTargetsPreserveExactPair() {
        val selected = NexusIdJumpPolicy.parse("50535", "190561")
        assertEquals("50535", selected?.modId)
        assertEquals("190561", selected?.fileId)
        assertEquals("178239", NexusIdJumpPolicy.parse("50535", "178239")?.fileId)
        assertEquals(null, NexusIdJumpPolicy.parse(" 50535 ", " ")?.fileId)
    }

    @Test fun malformedOrAmbiguousIdsNeverNavigate() {
        val bad = listOf("", "0", "01", "-5", "12/34", "123?file=4", "9999999999999", "12\n3")
        bad.forEach { assertNull(NexusIdJumpPolicy.parse(it, "190561")) }
        bad.filter { it.isNotEmpty() }.forEach {
            assertNull(NexusIdJumpPolicy.parse("50535", it))
        }
        assertEquals(null, NexusIdJumpPolicy.parse("50535", "")?.fileId)
        assertNull(NexusIdJumpPolicy.parse("50535", "1&switch=2"))
        assertNull(NexusIdJumpPolicy.parse("50535", "123.4"))
    }
}
