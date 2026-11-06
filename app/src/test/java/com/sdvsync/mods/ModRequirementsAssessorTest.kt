package com.sdvsync.mods

import com.sdvsync.mods.models.InstalledMod
import com.sdvsync.mods.models.ModDependency
import com.sdvsync.mods.models.ModManifest
import com.sdvsync.mods.models.RemoteMod
import org.junit.Assert.*
import org.junit.Test

class ModRequirementsAssessorTest {
    private val remote = RemoteMod(sourceId="nexus",modId="101",name="Sample",
        author="Test",summary="Fixture",version="2.0")
    private fun local(id:String, version:String="1.0", enabled:Boolean=true,
        dependencies:List<ModDependency> = emptyList(),source:String?=null,
        packFor: com.sdvsync.mods.models.ContentPackFor?=null,
        minSmapi: String?=null) =
        InstalledMod(ModManifest(id,"Test",version,id,"",minimumApiVersion=minSmapi,
            contentPackFor=packFor,dependencies=dependencies),
            folderName=id,folderPath="fixture",enabled=enabled,installedFrom=source)

    @Test fun notInstalledCannotBeVerified() {
        val r=ModRequirementsAssessor.assess(remote,emptyList())
        assertEquals(RequirementVerdict.UNKNOWN,r.overall)
        assertFalse(r.installedSourceMatched)
    }
    @Test fun missingDependencyBlocks() {
        val r=ModRequirementsAssessor.assess(remote,listOf(
            local("main",dependencies=listOf(ModDependency("missing","2.0")),source="nexus:101")))
        assertEquals(RequirementVerdict.BLOCKED,r.overall)
    }
    @Test fun disabledProviderBlocks() {
        val r=ModRequirementsAssessor.assess(remote,listOf(
            local("main",dependencies=listOf(ModDependency("provider")),source="nexus:101"),
            local("provider",enabled=false)))
        assertEquals(RequirementVerdict.BLOCKED,r.overall)
    }
    @Test fun oldVersionBlocks() {
        val r=ModRequirementsAssessor.assess(remote,listOf(
            local("main",dependencies=listOf(ModDependency("provider","4.0")),source="nexus:101"),
            local("provider","3.0")))
        assertEquals(RequirementVerdict.BLOCKED,r.overall)
    }
    @Test fun ambiguousVersionRequiresReview() {
        val r=ModRequirementsAssessor.assess(remote,listOf(
            local("main",dependencies=listOf(ModDependency("provider","2.0-beta")),source="nexus:101"),
            local("provider","2.0-rc")))
        assertEquals(RequirementVerdict.REVIEW,r.overall)
    }
    @Test fun satisfiedManifestStillNotAndroidCompatible() {
        val r=ModRequirementsAssessor.assess(remote,listOf(
            local("main",dependencies=listOf(ModDependency("provider","2.0")),source="nexus:101"),
            local("provider","2.5")))
        assertEquals(RequirementVerdict.UNKNOWN,r.overall)
        assertTrue(r.findings.any { it.title.contains("provider") &&
            it.verdict==RequirementVerdict.CHECKED })
    }
    @Test fun unreadableInventoryIsUnknown() {
        assertEquals(RequirementVerdict.UNKNOWN,ModRequirementsAssessor.assess(remote,null).overall)
    }
    @Test fun optionalMissingDependencyNeedsReview() {
        val report=ModRequirementsAssessor.assess(remote,listOf(
            local("main",dependencies=listOf(ModDependency("optional",null,false)),source="nexus:101")))
        assertEquals(RequirementVerdict.REVIEW,report.overall)
        assertTrue(report.findings.any { it.title.contains("optional") &&
            it.verdict==RequirementVerdict.REVIEW })
    }
    @Test fun contentPackProviderIsRequired() {
        val report=ModRequirementsAssessor.assess(remote,listOf(
            local("pack",packFor=com.sdvsync.mods.models.ContentPackFor("framework","2.0"),
                source="nexus:101")))
        assertEquals(RequirementVerdict.BLOCKED,report.overall)
        assertTrue(report.findings.any { it.title.contains("Content-pack") })
    }
    @Test fun duplicateDependenciesCannotBeDeclaredSatisfied() {
        val report=ModRequirementsAssessor.assess(remote,listOf(
            local("main",dependencies=listOf(ModDependency("provider")),source="nexus:101"),
            local("provider","1.0"),local("provider","1.1")))
        assertEquals(RequirementVerdict.BLOCKED,report.overall)
    }
    @Test fun minimumSmapiVersionStillRequiresRuntimeEvidence() {
        val report=ModRequirementsAssessor.assess(remote,listOf(
            local("main",source="nexus:101",minSmapi="4.0")))
        assertEquals(RequirementVerdict.UNKNOWN,report.overall)
        assertTrue(report.findings.any { it.title=="Minimum SMAPI" &&
            it.verdict==RequirementVerdict.UNKNOWN })
    }
    @Test fun nonNexusSourceBindingCannotImpersonateNexusListing() {
        val report=ModRequirementsAssessor.assess(remote,listOf(
            local("main",source="github:101")))
        assertEquals(RequirementVerdict.UNKNOWN,report.overall)
        assertFalse(report.installedSourceMatched)
    }
    @Test fun duplicateSourceBindingBlocks() {
        assertEquals(RequirementVerdict.BLOCKED,ModRequirementsAssessor.assess(remote,listOf(
            local("one",source="nexus:101"),local("two",source="nexus:101"))).overall)
    }
}
