"""Non-mutating M23 source gates and negative provenance assertions."""
import copy
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import m23_discovery_gate as gate

class M23HostTests(unittest.TestCase):
    def test_source_gate_passes_and_is_not_device_proof(self):
        r=gate.generate(gate.ROOT,{})
        self.assertEqual(r['overall'],'PASS_M23_SOURCE_INVENTORY')
        self.assertEqual(r['real_device_inventory'],'NOT_RUN')
        self.assertFalse(r['m23_device_qualified'])
        self.assertFalse(r['publication_allowed'])
        self.assertGreaterEqual(len(r['source_sha256']),12)

    def test_github_sha_rejects_mismatch(self):
        with self.assertRaises(gate.GateError):
            gate.generate(gate.ROOT,{'GITHUB_SHA':'0'*40})

    def test_github_repository_rejects_mismatch(self):
        with self.assertRaises(gate.GateError):
            gate.generate(gate.ROOT,{'GITHUB_REPOSITORY':'attacker/copy'})

    def test_policy_cannot_be_overridden(self):
        orig=gate.safe
        def changed(root,path):
            if path=='docs/security/M3_RELEASE_POLICY.json':
                return orig(root,path).replace(b'"publication_enabled": false',b'"publication_enabled": true')
            return orig(root,path)
        with patch.object(gate,'safe',side_effect=changed):
            with self.assertRaises(gate.GateError): gate.generate(gate.ROOT,{})

    def test_source_guard_cannot_be_removed(self):
        original=gate.safe
        def changed(root,path):
            data=original(root,path)
            if path.endswith('GameDownloadViewModel.kt'):
                return data.replace(b'M23CinderboxFirstPolicy.assess(',b'M23CinderboxFirstPolicy.omitted(')
            return data
        with patch.object(gate,'safe',side_effect=changed):
            with self.assertRaises(gate.GateError): gate.generate(gate.ROOT,{})

    def test_main_download_manager_guard_cannot_be_removed(self):
        original=gate.safe
        def changed(root,path):
            data=original(root,path)
            if path.endswith('GameDownloadManager.kt'):
                return data.replace(b'check(scope.separateEmptyDestination)',b'check(true)')
            return data
        with patch.object(gate,'safe',side_effect=changed):
            with self.assertRaises(gate.GateError):gate.generate(gate.ROOT,{})

    def test_readonly_observation_cannot_become_write_probe(self):
        original=gate.safe
        def changed(root,path):
            data=original(root,path)
            if path.endswith('InstallationScanner.kt'):
                return data + b'\n// StoragePreflight.check(selectedGameDir)\n'
            return data
        with patch.object(gate,'safe',side_effect=changed):
            with self.assertRaises(gate.GateError): gate.generate(gate.ROOT,{})

    def test_safety_bound_is_source_contract(self):
        original=gate.safe
        def changed(root,path):
            data=original(root,path)
            if path.endswith('M23InstallationDiscovery.kt'):
                return data.replace(b'MAX_CHILDREN = 256',b'MAX_CHILDREN = 1000000')
            return data
        with patch.object(gate,'safe',side_effect=changed):
            with self.assertRaises(gate.GateError): gate.generate(gate.ROOT,{})

    def test_native_dag_not_a_homegrown_installer(self):
        r=gate.generate(gate.ROOT,{})
        self.assertTrue(r['safety']['no_recursive_scan'])
        self.assertIn('scripts/devtool/m23_discovery_gate.py',r['source_sha256'])

if __name__=='__main__':unittest.main()
