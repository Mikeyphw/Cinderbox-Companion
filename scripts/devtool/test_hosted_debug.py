"""Offline behavior checks for source/branch-bound Devtool dispatch bridge."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch, call

P = Path(__file__).with_name('hosted_debug.py')
sp = importlib.util.spec_from_file_location('hosted_debug', P)
h = importlib.util.module_from_spec(sp)
sp.loader.exec_module(h)


class HostedDebugTests(unittest.TestCase):
    def test_plan_targets_actual_branch_without_hardcoded_master(self):
        command=h.make_command('plan',branch='feature/m24-steam-download-safety')
        self.assertEqual(command[command.index('--ref')+1], 'feature/m24-steam-download-safety')
        self.assertEqual(command[command.index('--input')+1], 'project_dir=.')
        self.assertNotIn('--yes',command)
        self.assertIn('--json',command)

    def test_run_requires_explicit_confirmation(self):
        with self.assertRaises(SystemExit):
            h.main(['run'])
        cmd=h.make_command('run',branch='feature/m24-steam-download-safety')
        self.assertEqual(cmd.count('--yes'),1)
        self.assertEqual(cmd.count('--input'),len(h.INPUTS))

    def test_invalid_request_id_refused(self):
        with self.assertRaises(ValueError):
            h.make_command('artifacts',request_id='123')
        self.assertEqual(h.make_command('watch',request_id='a'*32)[-3:],['--request-id','a'*32,'--json'])

    def test_exact_sha_and_clean_worktree(self):
        sha='b'*40
        def mocked(*argv):
            if argv[1]=='symbolic-ref': return 'feature/m24-steam-download-safety'
            if argv[1]=='status': return ''
            if argv[1]=='rev-parse': return sha
            if argv[0]=='gh': return '{"object":{"sha":"'+sha+'"}}'
            raise AssertionError(argv)
        with patch.object(h,'output',side_effect=mocked) as mocked_output:
            self.assertEqual(h.source_identity(),('feature/m24-steam-download-safety',sha))
            path=mocked_output.call_args_list[-1].args[-1]
            self.assertIn('/git/ref/heads/feature/m24-steam-download-safety',path)

    def test_remote_divergence_refused(self):
        with patch.object(h,'output',side_effect=['feature/m24-steam-download-safety','','b'*40,'{"object":{"sha":"c"}}']):
            with self.assertRaisesRegex(RuntimeError,'differs from GitHub'):
                h.source_identity()

    def test_dirty_tree_refused(self):
        with patch.object(h,'output',side_effect=['feature/m24-steam-download-safety',' M file']):
            with self.assertRaisesRegex(RuntimeError,'not clean'):
                h.source_identity()

    def test_detached_and_malformed_branch_refused(self):
        with patch.object(h,'output',return_value='invalid/../master'):
            with self.assertRaisesRegex(RuntimeError,'Unsafe'):
                h.source_identity()

    def test_other_repo_or_release_cannot_be_dispatched(self):
        command=h.make_command('run',branch='feature/m24-steam-download-safety')
        self.assertEqual(command[command.index('--github-repo')+1],h.REPO)
        self.assertNotIn('release',command)
        self.assertTrue(h.WORKFLOW in command)

if __name__ == '__main__': unittest.main()
