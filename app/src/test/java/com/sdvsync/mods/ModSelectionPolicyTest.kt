package com.sdvsync.mods

import com.sdvsync.mods.models.ContentPackFor
import com.sdvsync.mods.models.InstalledMod
import com.sdvsync.mods.models.ModDependency
import com.sdvsync.mods.models.ModManifest
import org.junit.Assert.*
import org.junit.Test

class ModSelectionPolicyTest {
    private fun mod(id: String, folder: String = id, enabled: Boolean = true,
        author: String = "Fixture", pack: Boolean = false,
        required: List<ModDependency> = emptyList()): InstalledMod = InstalledMod(
        ModManifest(name = id, author = author, description = "Synthetic", version = "1.0.0",
            uniqueID = id, dependencies = required,
            contentPackFor = if (pack) ContentPackFor("Framework.Mod") else null),
        folderName = folder, folderPath = "", enabled = enabled)

    @Test fun groupsClassifyWithoutMutation() {
        val framework = mod("Framework.Mod", author = "Amber")
        val pack = mod("Sample.Pack", pack = true, author = "Beryl")
        assertTrue(ModSelectionPolicy.matches(framework, ModGroupMode.FRAMEWORK, emptySet(), emptySet()))
        assertFalse(ModSelectionPolicy.matches(pack, ModGroupMode.FRAMEWORK, emptySet(), emptySet()))
        assertTrue(ModSelectionPolicy.matches(pack, ModGroupMode.CONTENT_PACK, emptySet(), emptySet()))
        assertTrue(ModSelectionPolicy.matches(pack, ModGroupMode.UPDATE_ATTENTION,
            setOf("sample.pack"), emptySet()))
        assertEquals("Amber", ModSelectionPolicy.section(framework, ModGroupMode.BY_AUTHOR))
        assertTrue(ModSelectionPolicy.matches(pack, ModGroupMode.COMPATIBILITY,
            emptySet(), setOf("sample.pack")))
    }

    @Test fun dependencyBlockerRejectsProviderDisable() {
        val provider = mod("Framework.Mod")
        val child = mod("Client.Mod", required = listOf(ModDependency("Framework.Mod")))
        val review = ModSelectionPolicy.preview(listOf(provider,child), setOf("Framework.Mod"), false)
        assertTrue(review.blockers.any { it.message.contains("Disabled dependency") })
        assertEquals(listOf("Framework.Mod"), review.steps.map { it.uniqueId })
    }

    @Test fun deterministicAndCaseInsensitiveSelection() {
        val a = mod("A.Mod", ".A", false)
        val b = mod("B.Mod", "B", true)
        val p = ModSelectionPolicy.preview(listOf(b,a), setOf("a.mod"), true)
        assertTrue(p.blockers.isEmpty())
        assertEquals(listOf("a.mod"),p.selectedIds)
        assertEquals(listOf("A"),p.steps.map { it.toFolder })
        assertEquals(p, ModSelectionPolicy.preview(listOf(a,b), setOf("A.MOD"), true))
    }

    @Test fun staleFingerprintCannotBeReused() {
        val list = listOf(mod("A", ".A", false))
        val p = ModSelectionPolicy.preview(list, setOf("A"), true)
        assertTrue(ModSelectionPolicy.stillMatches(p,list))
        assertFalse(ModSelectionPolicy.stillMatches(p,listOf(list[0].copy(enabled=true))))
    }

    @Test fun duplicateAndMissingIdsFailClosed() {
        val mods = listOf(mod("A", "A"),mod("a", "a2"))
        val p = ModSelectionPolicy.preview(mods,setOf("A","Absent"),false)
        assertTrue(p.blockers.any { it.message.contains("Missing or duplicate") })
    }

    @Test fun destinationCollisionAndUnsafeNamesFailClosed() {
        val mods = listOf(mod("A", ".A", false), mod("B", "A", true))
        val p = ModSelectionPolicy.preview(mods,setOf("A"),true)
        assertTrue(p.blockers.any { it.message.contains("collision") })
        val malformed = ModSelectionPolicy.preview(listOf(mod("X", "../X")),setOf("X"),false)
        assertTrue(malformed.blockers.any { it.message.contains("Unsafe folder") })
    }

    @Test fun emptyAndOversizeSelectionNeverProduceExecutablePlan() {
        assertTrue(ModSelectionPolicy.preview(listOf(mod("A")), emptySet(),false).blockers.isNotEmpty())
        val mods = (0..512).map { mod("M$it") }
        assertTrue(ModSelectionPolicy.preview(mods,setOf("M0"),false).blockers.any {
            it.message.contains("512") })
    }
}
