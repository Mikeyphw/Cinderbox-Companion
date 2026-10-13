package com.sdvsync.util

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ZipBudgetTest {
    @Test fun acceptsNormalEntry() {
        val data = ByteArray(200) { it.toByte() }
        val budget = ZipBudget(2, 512, 600)
        budget.nextEntry()
        val out = ByteArrayOutputStream()
        budget.copyEntry(ByteArrayInputStream(data), out)
        assertArrayEquals(data, out.toByteArray())
    }

    @Test fun rejectsTooManyEntries() {
        val budget = ZipBudget(1, 1024, 1024)
        budget.nextEntry()
        assertTrue(runCatching { budget.nextEntry() }.isFailure)
    }

    @Test fun rejectsEntryAndCumulativeOverflows() {
        val perEntry = ZipBudget(3, 5, 30)
        perEntry.nextEntry()
        assertTrue(runCatching { perEntry.readEntry(ByteArrayInputStream(ByteArray(6))) }.isFailure)
        val cumulative = ZipBudget(3, 10, 10)
        cumulative.nextEntry()
        cumulative.readEntry(ByteArrayInputStream(ByteArray(6)))
        cumulative.nextEntry()
        assertTrue(runCatching { cumulative.readEntry(ByteArrayInputStream(ByteArray(6))) }.isFailure)
    }
}
