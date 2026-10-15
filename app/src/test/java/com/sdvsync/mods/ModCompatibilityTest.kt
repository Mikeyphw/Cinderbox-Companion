package com.sdvsync.mods

import com.sdvsync.mods.models.ContentPackFor
import com.sdvsync.mods.models.InstalledMod
import com.sdvsync.mods.models.ModDependency
import com.sdvsync.mods.models.ModManifest
import com.sdvsync.mods.models.ModProfile
import org.junit.Assert.*
import org.junit.Test

class ModCompatibilityTest {
    private fun mod(id: String, version: String = "1.0.0", enabled: Boolean = true,
                    deps: List<ModDependency> = emptyList(),
                    pack: ContentPackFor? = null): InstalledMod = InstalledMod(
        manifest = ModManifest(id, "Test", version, id, description = "", dependencies = deps, contentPackFor = pack),
        folderName = if (enabled) id else ".$id", folderPath = "/mods/$id", enabled = enabled
    )
    @Test fun missingRequiredDependencyBlocksProfile() {
        val m = mod("addon", deps = listOf(ModDependency("base", isRequired = true)))
        val preview = ModCompatibility.preview(listOf(m), ModProfile("x", setOf("addon")))
        assertTrue(preview.blockers.any { it.message.contains("Missing") })
    }
    @Test fun missingOptionalDependencyDoesNotBlock() {
        val m = mod("addon", deps = listOf(ModDependency("optional", isRequired = false)))
        assertTrue(ModCompatibility.preview(listOf(m), ModProfile("x", setOf("addon"))).blockers.isEmpty())
    }
    @Test fun insufficientVersionBlocksAndEqualVersionPasses() {
        val addon = mod("addon", deps = listOf(ModDependency("base", "2.0.0")))
        assertTrue(ModCompatibility.preview(listOf(addon, mod("base", "1.9.9")),
            ModProfile("x", setOf("addon", "base"))).blockers.isNotEmpty())
        assertTrue(ModCompatibility.preview(listOf(addon, mod("base", "2.0.0")),
            ModProfile("x", setOf("addon", "base"))).blockers.isEmpty())
    }
    @Test fun profileShowsDisableAndEnableAndRequiredDependency() {
        val addon = mod("addon", enabled = false, deps = listOf(ModDependency("base")))
        val base = mod("base")
        val preview = ModCompatibility.preview(listOf(addon, base), ModProfile("x", setOf("addon")))
        assertEquals(2, preview.steps.size)
        assertTrue(preview.steps.any { it.fromFolder == "base" && it.toFolder == ".base" })
        assertTrue(preview.steps.any { it.fromFolder == ".addon" && it.toFolder == "addon" })
        assertTrue(preview.blockers.any { it.message.contains("Disabled") })
    }
    @Test fun caseInsensitiveIdsAndFingerprintChanges() {
        val a = mod("Test.Mod", enabled = false)
        val preview = ModCompatibility.preview(listOf(a), ModProfile("x", setOf("test.mod")))
        assertTrue(preview.blockers.isEmpty())
        assertEquals("Test.Mod", preview.steps.single().toFolder)
        assertNotEquals(ModCompatibility.fingerprint(listOf(a)),
            ModCompatibility.fingerprint(listOf(mod("Test.Mod", enabled = true))))
    }
    @Test fun dependencyEditInvalidatesApprovedProfilePreview() {
        val original = mod("addon", deps = listOf(ModDependency("base", isRequired = false)))
        val altered = mod("addon", deps = listOf(ModDependency("base", isRequired = true)))
        assertNotEquals(ModCompatibility.fingerprint(listOf(original)),
            ModCompatibility.fingerprint(listOf(altered)))
    }
    @Test fun profileFingerprintChangesForContentPackProvider() {
        val a = mod("pack", pack = ContentPackFor("one", "1.0"))
        val b = mod("pack", pack = ContentPackFor("two", "1.0"))
        assertNotEquals(ModCompatibility.fingerprint(listOf(a)),
            ModCompatibility.fingerprint(listOf(b)))
    }
    @Test fun duplicateIdAndMissingProfileModBlocked() {
        val a = mod("AAA")
        val b = mod("aaa")
        val preview = ModCompatibility.preview(listOf(a,b), ModProfile("x", setOf("AAA", "missing")))
        assertTrue(preview.blockers.any { it.message.contains("Duplicate") })
        assertTrue(preview.blockers.any { it.message.contains("missing mod") })
    }
    @Test fun contentPackProviderMustBePresent() {
        val pack = mod("pack", pack = ContentPackFor("provider", "1.3.0"))
        val preview = ModCompatibility.preview(listOf(pack), ModProfile("x", setOf("pack")))
        assertTrue(preview.blockers.any { it.message.contains("provider") })
    }
    @Test fun unfamiliarVersionsFailConservatively() {
        assertNull(ModCompatibility.atLeast("whatever", "1.0.0"))
        assertFalse(ModCompatibility.atLeast("1.4.9", "1.5.0")!!)
        assertTrue(ModCompatibility.atLeast("2.0.0", "1.5.0")!!)
        assertFalse(ModCompatibility.atLeast("1.5.0-beta", "1.5.0")!!)
    }
}
