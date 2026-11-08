package com.sdvsync.mods.api

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class NexR1CatalogContractTest {
    @Suppress("UNCHECKED_CAST")
    private fun clauses(op: NexusSearchOperation): List<Map<String, Any>> =
        (op.variables.getValue("filter") as Map<String, Any>).getValue("filter") as List<Map<String, Any>>

    private fun hasClause(clauses: List<Map<String, Any>>, field: String, value: String, operator: String): Boolean =
        clauses.any { c ->
            val x = c[field] as? Map<*, *> ?: return@any false
            x["value"] == value && x["op"] == operator
        }

    @Test fun everyRequestIsPinnedToStardewAndNeverConcatenatesInput() {
        val phrase = "Stardew \"escape\" $" + "query"
        val op = createNexusCatalogOperation(phrase, page = 2)
        assertTrue(hasClause(clauses(op), "gameId", "1303", "EQUALS"))
        assertTrue(hasClause(clauses(op), "name", phrase, "WILDCARD"))
        assertFalse(op.document.contains(phrase))
        assertEquals(50, op.variables["offset"])
    }

    @Test fun serverSideFiltersCombineAndPaginate() {
        val f = NexusCatalogFilters(
            categoryName = "Gameplay Mechanics", includeTag = "SMAPI", excludeTag = "Translation",
            updatedWithinDays = 30, minDownloads = 100, minEndorsements = 10,
            sort = NexusCatalogSort.UPDATED
        )
        val op = createNexusCatalogOperation("", f, page = 3, nowEpochSeconds = 1_800_000_000L)
        val c = clauses(op)
        assertTrue(hasClause(c, "categoryName", "Gameplay Mechanics", "EQUALS"))
        assertTrue(hasClause(c, "tag", "SMAPI", "EQUALS"))
        assertTrue(hasClause(c, "tag", "Translation", "NOT_EQUALS"))
        assertTrue(hasClause(c, "updatedAt", (1_800_000_000L - 30 * 86400L).toString(), "GT"))
        assertTrue(hasClause(c, "downloads", "99", "GT"))
        assertTrue(hasClause(c, "endorsements", "9", "GT"))
        assertEquals(100, op.variables["offset"])
        assertTrue(op.variables.getValue("sort").toString().contains("updatedAt"))
    }

    @Test fun blankSearchSupportsEntireCatalogAndInputsAreBounded() {
        val f = NexusCatalogFilters(categoryName = "x".repeat(400), minDownloads = Int.MAX_VALUE,
            updatedWithinDays = -10)
        val op = createNexusCatalogOperation("", f)
        assertEquals(0, op.variables["offset"])
        assertTrue(hasClause(clauses(op), "categoryName", "x".repeat(64), "EQUALS"))
        assertFalse(clauses(op).any { it.containsKey("updatedAt") })
        assertTrue(hasClause(clauses(op), "downloads", "9999999", "GT"))
    }

    @Test fun rejectsOneLetterSearchAndUnboundedPage() {
        try { createNexusCatalogOperation("x"); throw AssertionError("must refuse short query") }
        catch (_: IllegalArgumentException) {}
        try { createNexusCatalogOperation("", page = 10001); throw AssertionError("must refuse huge page") }
        catch (_: IllegalArgumentException) {}
    }
}
