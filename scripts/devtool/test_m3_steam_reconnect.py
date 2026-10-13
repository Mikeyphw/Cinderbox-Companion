#!/usr/bin/env python3
"""Offline regression checks for M3E's connection-aware Steam branch UI.

These are source-contract checks, not a substitute for Gradle/Android CI or
real-device Steam testing. No Steam account or network access is needed.
"""
from __future__ import annotations
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2] if 'scripts' in Path(__file__).parts else None

# This test module is installed to scripts/devtool/test_m3_steam_reconnect.py.
# It may also be run from the standalone overlay bundle in an offline fixture.


class SteamBranchScreenContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Path(__file__).resolve().parents[2]
        cls.vm_path = cls.repo / 'app/src/main/java/com/sdvsync/ui/viewmodels/GameDownloadViewModel.kt'
        cls.ui_path = cls.repo / 'app/src/main/java/com/sdvsync/ui/screens/GameDownloadScreen.kt'
        cls.di_path = cls.repo / 'app/src/main/java/com/sdvsync/di/AppModule.kt'
        cls.res_path = cls.repo / 'app/src/main/res/values/strings.xml'
        if not cls.vm_path.exists():
            raise unittest.SkipTest('No installed Android source checkout: run fixture tests instead')
        cls.vm = cls.vm_path.read_text()
        cls.ui = cls.ui_path.read_text()
        cls.di = cls.di_path.read_text()
        cls.res = cls.res_path.read_text()

    def test_async_pics_request_requires_session(self):
        self.assertLess(self.vm.index('if (!steamClientManager.isLoggedIn)'), self.vm.index('contentService.getAppBranches()'))
        self.assertIn('steamClientManager.awaitLoggedIn(timeoutMs)', self.vm)

    def test_initial_load_does_not_initiate_new_authentication(self):
        self.assertIn('fun loadBranches(reconnect: Boolean = false)', self.vm)
        self.assertIn('if (reconnect && steamClientManager.connectionState.value != ConnectionState.CONNECTING)', self.vm)
        self.assertIn('steamAuthenticator.loginWithSavedSession()', self.vm)

    def test_cancellation_is_not_suppressed(self):
        fragment = self.vm.split('fun loadBranches(reconnect: Boolean = false)', 1)[1].split('fun selectBranch', 1)[0]
        self.assertIn('catch (e: CancellationException)', fragment)
        self.assertIn('throw e', fragment)

    def test_failed_jobs_and_empty_branches_offer_retry(self):
        self.assertIn('download_error_no_branches', self.vm)
        self.assertIn('branchLoadNeedsReconnect = disconnected', self.vm)
        self.assertIn('fun retryBranchLoad() = loadBranches(reconnect = true)', self.vm)
        self.assertIn('onClick = viewModel::retryBranchLoad', self.ui)

    def test_steam_logged_in_state_is_observed_and_download_is_fail_closed(self):
        self.assertIn('steamClientManager.connectionState.collect', self.vm)
        self.assertIn('steamLoggedIn = connection == ConnectionState.LOGGED_IN', self.vm)
        self.assertIn('if (!steamClientManager.isLoggedIn) {', self.vm.split('fun startDownload()', 1)[1][:450])
        self.assertIn('enabled = state.branches.isNotEmpty() && state.steamLoggedIn && !state.isLoadingBranches', self.ui)

    def test_reconnect_job_does_not_overlap(self):
        self.assertIn('if (branchLoadJob?.isActive == true) return', self.vm)
        self.assertIn('branchLoadJob = viewModelScope.launch', self.vm)

    def test_di_resolves_shared_steam_singletons(self):
        self.assertIn('single { SteamAuthenticator(androidContext(), get(), get()) }', self.di)
        self.assertIn('single { SteamClientManager(androidContext(), get()) }', self.di)
        self.assertIn('viewModel { GameDownloadViewModel(androidContext(), get(), get(), get(), get(), get(), get()) }', self.di)

    def test_messages_are_localized_and_error_does_not_show_exception_body(self):
        self.assertIn('R.string.download_error_steam_offline', self.vm)
        self.assertIn('e.javaClass.simpleName', self.vm)
        self.assertNotIn('download_error_load_branches, e.message', self.vm)
        for key in ('download_error_steam_offline','download_error_no_branches','download_retry_steam','download_retry_branches'):
            self.assertIn(f'name="{key}"', self.res)
        self.assertIn('Reconnect Steam &amp; Retry', self.res)


if __name__ == '__main__':
    unittest.main()
