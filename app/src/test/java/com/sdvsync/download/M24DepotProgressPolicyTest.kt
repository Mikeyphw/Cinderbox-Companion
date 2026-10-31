package com.sdvsync.download

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class M24DepotProgressPolicyTest {
    @Test fun zeroIsUnknownEvenAfterRealBytes() {
        assertNull(M24DepotProgressPolicy.displayedDepotPercent(0f, 54_600_000L))
        assertNull(M24DepotProgressPolicy.displayedDepotPercent(0f, 0L))
    }

    @Test fun nonFiniteAndUnboundedValuesAreUnknown() {
        assertNull(M24DepotProgressPolicy.displayedDepotPercent(Float.NaN, 100L))
        assertNull(M24DepotProgressPolicy.displayedDepotPercent(Float.POSITIVE_INFINITY, 100L))
        assertNull(M24DepotProgressPolicy.displayedDepotPercent(-0.1f, 100L))
        assertNull(M24DepotProgressPolicy.displayedDepotPercent(1.01f, 100L))
    }

    @Test fun validPerDepotProgressIsDisplayedOnlyWithContent() {
        assertEquals(50, M24DepotProgressPolicy.displayedDepotPercent(.5f, 100L))
        assertEquals(100, M24DepotProgressPolicy.displayedDepotPercent(1f, 100L))
        assertNull(M24DepotProgressPolicy.displayedDepotPercent(.5f, 0L))
    }
}
