package com.sdvsync.qualification

import android.os.Bundle
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/** Separate uncounted maintenance class. No raw paths or tokens in Android status. */
@RunWith(AndroidJUnit4::class)
class M20FixtureMaintenanceDeviceTest {
    @Test fun inspectOwnedInventory() {
        val ids = M20OwnedFixtures.inventory()
        check(ids.size <= 1000) { "M20_INVENTORY_TOO_LARGE" }
        val result = ids.joinToString(",")
        check(result.length <= 40000) { "M20_INVENTORY_TOO_LARGE" }
        InstrumentationRegistry.getInstrumentation().sendStatus(2, Bundle().apply {
            putString("m20_inventory", result)
        })
        assertTrue(ids.all { it.matches(Regex("[0-9a-f]{24}|m19-unverified:[0-9a-f]{24}")) })
    }
    @Test fun cleanupVerifiedFixture() {
        val args = InstrumentationRegistry.getArguments()
        check(args.getString("m20_maintenance_opt_in") == "true") { "M20_CLEANUP_CONSENT_REQUIRED" }
        val selector = args.getString("m20_cleanup_id") ?: ""
        when {
            selector.matches(Regex("m20:[0-9a-f]{24}")) ->
                M20OwnedFixtures.cleanupByOpaqueId(selector.removePrefix("m20:"))
            selector.matches(Regex("m19:[0-9a-f]{24}")) ->
                M20OwnedFixtures.cleanupLegacyM19(selector.removePrefix("m19:"))
            else -> error("M20_CLEANUP_SELECTOR_INVALID")
        }
        InstrumentationRegistry.getInstrumentation().sendStatus(2, Bundle().apply {
            putString("m20_cleanup_verified", "true")
        })
    }
}
