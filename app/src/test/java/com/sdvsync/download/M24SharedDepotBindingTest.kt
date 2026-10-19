package com.sdvsync.download

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class M24SharedDepotBindingTest {
    private val direct = mapOf(413151 to "12345")
    private val parents = mapOf(229002 to 228980, 229012 to 228980)
    @Test fun parentPicsIdsCompleteSetSucceeds() {
        val verified = M24SharedDepotBinding.merge(direct, parents, mapOf(229002 to "9999", 229012 to "8888"))
        assertEquals(setOf(413151, 229002, 229012), verified.keys)
    }
    @Test fun partialParentCannotAuthorize() {
        assertThrows(IllegalArgumentException::class.java) {
            M24SharedDepotBinding.merge(direct, parents, mapOf(229002 to "9999"))
        }
    }
    @Test fun spuriousParentDepotCannotAuthorize() {
        assertThrows(IllegalArgumentException::class.java) {
            M24SharedDepotBinding.merge(direct, parents,
                mapOf(229002 to "9999", 229012 to "8888", 229999 to "5"))
        }
    }
    @Test fun mismatchedDirectDepotCannotAuthorize() {
        assertThrows(IllegalArgumentException::class.java) {
            M24SharedDepotBinding.merge(direct, mapOf(413151 to 228980),
                mapOf(413151 to "9999"))
        }
    }
    @Test fun noSharedDepotsRetainOriginal() {
        assertEquals(direct, M24SharedDepotBinding.merge(direct, emptyMap(), emptyMap()))
    }
}
