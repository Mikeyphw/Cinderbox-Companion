package com.sdvsync.mods

import org.junit.Assert.*
import org.junit.Test

class NexusLab04SyntheticPolicyTest {
    private val digest = "b".repeat(64)

    @Test fun onlyFreshEmptyLabRootCanInstall() {
        assertTrue(NexusLab04SyntheticPolicy.mayInstall(null, true))
        for (phase in listOf("INSTALLING", "INSTALLED", "ROLLING_BACK", "ROLLED_BACK")) {
            assertFalse(NexusLab04SyntheticPolicy.mayInstall(phase, true))
        }
        assertFalse(NexusLab04SyntheticPolicy.mayInstall(null, false))
    }

    @Test fun rollbackRequiresExactVerifiedInstalledBytes() {
        assertTrue(NexusLab04SyntheticPolicy.mayRollback("INSTALLED", true))
        assertFalse(NexusLab04SyntheticPolicy.mayRollback("INSTALLED", false))
        assertFalse(NexusLab04SyntheticPolicy.mayRollback("INSTALLING", true))
        assertFalse(NexusLab04SyntheticPolicy.mayRollback("ROLLED_BACK", true))
    }

    @Test fun strictNonRecoverableCrashStates() {
        assertTrue(NexusLab04SyntheticPolicy.allowedTransition(null, "INSTALLING"))
        assertTrue(NexusLab04SyntheticPolicy.allowedTransition("INSTALLING", "INSTALLED"))
        assertTrue(NexusLab04SyntheticPolicy.allowedTransition("INSTALLED", "ROLLING_BACK"))
        assertTrue(NexusLab04SyntheticPolicy.allowedTransition("ROLLING_BACK", "ROLLED_BACK"))
        assertFalse(NexusLab04SyntheticPolicy.allowedTransition(null, "INSTALLED"))
        assertFalse(NexusLab04SyntheticPolicy.allowedTransition("ROLLING_BACK", "INSTALLED"))
        assertFalse(NexusLab04SyntheticPolicy.allowedTransition("ROLLED_BACK", "INSTALLING"))
    }

    @Test fun receiptRejectsProvenanceOrSyntheticIdentityDrift() {
        val p = NexusLab04SyntheticPolicy
        fun valid(scope:String=p.SCOPE, source:String=p.SOURCE, sha:String=digest,
                  folder:String=p.FOLDER, phase:String="INSTALLED", nx:Boolean=false, production:Boolean=false) =
            p.validReceipt(p.SCHEMA,scope,source,sha,folder,phase,nx,production)
        assertTrue(valid())
        assertFalse(valid(scope="NEXUS_VERIFIED"))
        assertFalse(valid(source="REMOTE_PROVIDER"))
        assertFalse(valid(sha="bad"))
        assertFalse(valid(folder="../OtherMod"))
        assertFalse(valid(phase="COMPLETE"))
        assertFalse(valid(nx=true))
        assertFalse(valid(production=true))
    }
}
