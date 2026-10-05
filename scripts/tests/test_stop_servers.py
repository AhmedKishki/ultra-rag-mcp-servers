"""Regression tests for the collection's process stop.

Two kinds of evidence are used, and neither touches a process that was not
started here:

* a synthetic `/proc` tree, so a snapshot can be written by hand, including one
  where a PID has been reused between the snapshot and the signal, and
* disposable child processes of this test run, whose command lines are written by
  this test run.

`scripts/stop-servers.sh` is never asked to stop anything. Its `--dry-run` is the
only mode exercised end to end, and the only real signal is the one sent to a
disposable child through its own pidfd.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import collection_processes as stops

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "stop-servers.sh"
SLEEPER = "import time\ntime.sleep(30)\n"
APP = ["/opt/bin/research-rag", "start"]
GATEWAY = ["/opt/bin/research-rag-gateway"]
RUNTIME = "/home/u/.cache/vanilla-ultra-rag-mcp/runtime/UltraRAG-abc/servers"
WAIT = 5.0
#: Handles are faked in every synthetic test, so no test can pass by depending on
#: a PID being absent: `stop` refuses to signal anything it has no handle for.
FAKE_HANDLE = 9000


class FakeProc:
    """A `/proc` tree written by hand, one directory per process."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def add(
        self,
        pid: int,
        argv: list[str],
        ppid: int = 1,
        start_time: int = 100,
        cwd: str | None = None,
        state: str = "S",
    ) -> None:
        directory = self.root / str(pid)
        directory.mkdir(parents=True, exist_ok=True)
        raw = b"\0".join(argument.encode() for argument in argv)
        (directory / "cmdline").write_bytes(raw + b"\0")
        # Fields after `comm`: `state` is field 3, `ppid` field 4, and
        # `starttime` field 22, which is index 19 counted from `state`.
        fields = [state, str(ppid)] + ["0"] * 17 + [str(start_time), "0"]
        (directory / "stat").write_text(f"{pid} (fake) {' '.join(fields)}\n")
        if cwd is not None:
            os.symlink(cwd, directory / "cwd")

    def forget(self, pid: int) -> None:
        shutil.rmtree(self.root / str(pid), ignore_errors=True)

    def retime(self, pid: int, start_time: int) -> None:
        fields = ["S", "1"] + ["0"] * 17 + [str(start_time), "0"]
        (self.root / str(pid) / "stat").write_text(f"{pid} (fake) {' '.join(fields)}\n")

    def zombie(self, pid: int) -> None:
        fields = ["Z", "1"] + ["0"] * 17 + ["0", "0"]
        (self.root / str(pid) / "stat").write_text(f"{pid} (fake) {' '.join(fields)}\n")


class FakeProcTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.proc = FakeProc(Path(self.directory.name))
        self.temp = Path(self.directory.name)

    def targets(self, project: str | None = None) -> dict[int, stops.Target]:
        return {
            target.pid: target
            for target in stops.select(project, proc_root=self.proc.root)
        }

    def handle(self, pid: int) -> int:
        return FAKE_HANDLE + pid

    def stop(self, targets, **kwargs):
        """A stop whose handles, signals, clock and waits are all synthetic."""

        recorded: list[tuple[int, int, int]] = []
        closed: list[int] = []
        clock = [0.0]

        def send(target: stops.Target, number: int, handle: int) -> bool:
            recorded.append((target.pid, number, handle))
            return True

        def sleep(seconds: float) -> None:
            clock[0] += seconds

        kwargs.setdefault("open_handle", self.handle)
        kwargs.setdefault("close_handle", closed.append)
        kwargs.setdefault("send", send)
        kwargs.setdefault("sleep", sleep)
        kwargs.setdefault("monotonic", lambda: clock[0])
        report = stops.stop(
            targets, kwargs.pop("timeout", 0), proc_root=self.proc.root, **kwargs
        )
        return report, recorded, closed


class RecognitionTest(unittest.TestCase):
    """What counts as a process this collection owns."""

    def test_a_console_script_is_recognised_by_its_own_path(self) -> None:
        for program, role in stops.SERVER_SCRIPTS.items():
            argv = [f"/opt/venv/bin/{program}", "--workspace-root", "/w"]
            self.assertEqual(stops.classify(*stops.program_of(argv)), role, program)

    def test_a_module_invocation_is_recognised(self) -> None:
        for module, role in stops.SERVER_MODULES.items():
            argv = ["/usr/bin/python3", "-m", module, "--project-root", "/w"]
            self.assertEqual(stops.classify(*stops.program_of(argv)), role, module)

    def test_an_interpreter_passes_the_script_after_itself(self) -> None:
        argv = ["/usr/bin/python3", "-u", "/opt/venv/bin/memory-ultra-rag-mcp", "-w"]
        self.assertEqual(stops.classify(*stops.program_of(argv)), "server")

    def test_an_interpreter_option_that_is_not_a_flag_ends_the_reading(self) -> None:
        refused = [
            ["/usr/bin/python3", "-c", "import time; time.sleep(30)"],
            ["/usr/bin/python3", "-cimport time"],
            ["/usr/bin/python3", "-"],
            ["/usr/bin/python3", "-i"],
            ["/usr/bin/python3", "-X", "dev", "/opt/bin/research-rag", "start"],
            ["/usr/bin/python3", "-W", "ignore", "/opt/bin/research-rag", "start"],
            ["/usr/bin/python3", "--", "/opt/bin/research-rag", "start"],
            ["/usr/bin/python3"],
            ["/usr/bin/python3", "-m"],
        ]
        for argv in refused:
            self.assertIsNone(stops.program_of(argv), argv)

    def test_env_passes_its_assignments_and_then_the_program(self) -> None:
        allowed = [
            ["env", "FOO=bar", "research-rag", "start"],
            [
                "env",
                "A=1",
                "B=2",
                "/opt/bin/research-rag-gateway",
                "--workspace-root",
                "/w",
            ],
        ]
        for argv in allowed:
            self.assertIsNotNone(stops.program_of(argv), argv)
        refused = [
            ["env", "-i", "research-rag", "start"],
            ["env", "--unset=FOO", "research-rag", "start"],
            ["env", "-S", "research-rag start"],
            ["env"],
        ]
        for argv in refused:
            self.assertIsNone(stops.program_of(argv), argv)

    def test_an_argument_naming_an_entry_point_is_not_a_server(self) -> None:
        innocent = [
            ["bash", "-c", "research-rag mcp --project-root /work/a"],
            ["vim", "/opt/venv/bin/research-rag-gateway"],
            ["grep", "-r", "memory-ultra-rag-mcp", "/work"],
            ["tail", "-f", "/var/log/research-rag.log"],
            ["sh", "-c", "exec -a research-rag sleep 1"],
        ]
        for argv in innocent:
            self.assertIsNone(stops.classify(*stops.program_of(argv)), argv)

    def test_ultrarag_children_are_recognised_on_their_own_path(self) -> None:
        argv = ["/usr/bin/python3", f"{RUNTIME}/corpus/src/corpus.py"]
        self.assertEqual(stops.classify(*stops.program_of(argv)), "ultrarag")
        elsewhere = ["/usr/bin/python3", "/work/corpus.py"]
        self.assertIsNone(stops.classify(*stops.program_of(elsewhere)))

    def test_the_apps_serving_forms_are_stopped(self) -> None:
        serving = [
            (["/usr/local/bin/research-rag"], "app", "a bare call serves the project"),
            (["/usr/local/bin/research-rag", "start"], "app", "start serves it"),
            (
                ["/usr/local/bin/research-rag", "mcp", "--project-name", "demo"],
                "app",
                "the stdio bridge",
            ),
            (
                ["/usr/local/bin/research-rag-gateway", "--workspace-root", "/w"],
                "gateway",
                "the gateway",
            ),
            (
                ["/usr/bin/python3", "-m", "memory_rag", "serve"],
                "app",
                "the app the launcher starts",
            ),
            (
                ["/usr/bin/python3", "-m", "memory_rag", "--storage-root", "/s", "mcp"],
                "app",
                "the stdio bridge",
            ),
            (
                ["/usr/local/bin/memory-rag", "serve", "--port", "8080"],
                "app",
                "the app in a terminal",
            ),
            (["/usr/local/bin/memory-rag", "mcp"], "app", "the stdio bridge"),
            (
                [
                    "/usr/bin/python3",
                    "/opt/venv/bin/memory-ultra-rag-mcp",
                    "--project-root",
                    "/w",
                ],
                "server",
                "the legacy stdio server",
            ),
        ]
        for argv, role, why in serving:
            self.assertEqual(stops.classify(*stops.program_of(argv)), role, why)

    def test_app_commands_that_answer_are_not_stopped(self) -> None:
        transient = [
            ["/usr/local/bin/research-rag", "status"],
            ["/usr/local/bin/research-rag", "--project-root", "/work/a", "status"],
            ["/usr/local/bin/research-rag", "config"],
            ["/usr/local/bin/research-rag", "clients"],
            ["/usr/local/bin/research-rag", "doctor", "--repair-runtime"],
            ["/usr/local/bin/research-rag", "ingest"],
            ["/usr/local/bin/research-rag", "stop"],
            ["/usr/local/bin/research-rag", "search", "start"],
            ["/usr/local/bin/research-rag", "--version"],
            ["/usr/local/bin/research-rag", "--project-root", "/work/a", "--version"],
            ["/usr/local/bin/research-rag", "help", "start"],
            ["/usr/local/bin/research-rag", "-h"],
            ["/usr/local/bin/memory-rag"],
            ["/usr/local/bin/memory-rag", "clients"],
            [
                "/usr/local/bin/memory-rag",
                "--project-root",
                "/work/a",
                "sql",
                "--execute",
            ],
            ["/usr/local/bin/memory-rag", "status"],
            ["/usr/local/bin/memory-rag", "start"],
            ["/usr/local/bin/memory-rag", "config"],
            ["/usr/local/bin/memory-rag", "reindex"],
            ["/usr/bin/python3", "-m", "memory_rag"],
            ["/usr/bin/python3", "-m", "memory_rag", "sql", "SELECT 1"],
            ["/opt/venv/bin/research-rag-runtime", "install"],
            ["/opt/venv/bin/memory-ultra-rag-reindex", "/work/a"],
        ]
        for argv in transient:
            self.assertIsNone(stops.classify(*stops.program_of(argv)), argv)

    def test_the_memory_app_is_the_only_account_wide_program(self) -> None:
        self.assertEqual(stops.scope_of("/opt/bin/memory-rag"), "account")
        self.assertEqual(stops.scope_of("memory_rag"), "account")
        self.assertEqual(stops.scope_of("/opt/bin/research-rag"), "project")

    def test_a_project_is_read_from_whole_arguments(self) -> None:
        space = stops.named_project(("--project-root=/work/a b",))
        self.assertEqual((space.option, space.value), ("--project-root", "/work/a b"))
        self.assertIsNone(stops.named_project(("--note", "/work/a")))
        self.assertIsNone(stops.named_project(("--project-root", "relative")) and None)


class SelectionTest(FakeProcTest):
    """Which of the recognised processes one run stops."""

    def test_a_project_is_matched_whole_and_not_as_a_prefix(self) -> None:
        self.proc.add(10, APP + ["--project-root", "/work/a"])
        self.proc.add(11, ["/opt/bin/research-rag", "--project-root=/work/a", "start"])
        self.proc.add(12, APP + ["--project-root", "/work/abc"])
        self.proc.add(13, APP + ["--note", "/work/a"])
        self.proc.add(14, APP + ["--project-root", "/work/a b"])
        self.assertEqual(sorted(self.targets("/work/a")), [10, 11])
        self.assertEqual(sorted(self.targets("/work/abc")), [12])
        self.assertEqual(sorted(self.targets("/work/a b")), [14])

    def test_a_gateway_names_its_project_and_keeps_its_children(self) -> None:
        workspace = "/work/a/.research-rag/runtime/ultrarag-runtime"
        self.proc.add(
            20,
            GATEWAY + ["--workspace-root", workspace, "--log-level", "warn"],
        )
        self.proc.add(
            21, ["/usr/bin/python3", f"{RUNTIME}/corpus/src/corpus.py"], ppid=20
        )
        self.proc.add(
            22, ["/usr/bin/python3", f"{RUNTIME}/retriever/src/retriever.py"], ppid=21
        )
        self.proc.add(23, GATEWAY + ["--workspace-root", "/work/other/.research-rag/x"])
        targets = self.targets("/work/a")
        self.assertEqual(sorted(targets), [20, 21, 22])
        self.assertEqual([targets[pid].depth for pid in (20, 21, 22)], [0, 1, 2])
        self.assertEqual(targets[20].project_path, "/work/a")
        self.assertEqual(targets[21].role, "ultrarag")

    def test_an_app_that_resolves_its_project_by_directory_is_selected(self) -> None:
        self.proc.add(30, ["/opt/bin/research-rag"], cwd="/work/a")
        self.proc.add(
            31, GATEWAY + ["--workspace-root", "/work/a/.research-rag/x"], ppid=30
        )
        self.proc.add(32, ["/opt/bin/memory-rag", "serve"], cwd="/work/a")
        self.assertEqual(sorted(self.targets("/work/a")), [30, 31])
        self.assertEqual(sorted(self.targets()), [30, 31, 32])

    def test_an_account_wide_app_is_never_selected_by_a_project(self) -> None:
        self.proc.add(33, ["/opt/bin/memory-rag", "serve"], cwd="/work/a")
        self.proc.add(
            34, ["/usr/bin/python3", "-m", "memory_rag", "mcp"], cwd="/work/a"
        )
        self.assertEqual(sorted(self.targets("/work/a")), [])
        self.assertEqual(sorted(self.targets()), [33, 34])

    def test_a_named_project_is_not_overridden_by_the_directory(self) -> None:
        self.proc.add(35, APP + ["--project-root", "/work/abc"], cwd="/work/a")
        self.proc.add(36, APP + ["--project-root", "/work/a"], cwd="/elsewhere")
        self.assertEqual(sorted(self.targets("/work/a")), [36])

    def test_a_relative_project_root_is_resolved_in_its_own_directory(self) -> None:
        project = self.temp / "work" / "a"
        (project / "sub").mkdir(parents=True)
        other = self.temp / "work" / "abc"
        (other / "sub").mkdir(parents=True)
        self.proc.add(37, APP + ["--project-root", "sub"], cwd=str(project))
        self.proc.add(38, APP + ["--project-root", "sub"], cwd=str(other))
        self.assertEqual(sorted(self.targets(str(project / "sub"))), [37])
        self.assertEqual(sorted(self.targets(str(other / "sub"))), [38])
        self.assertEqual(sorted(self.targets(str(project))), [])

    def test_a_relative_project_root_without_a_directory_is_refused(self) -> None:
        self.proc.add(39, APP + ["--project-root", "sub"], cwd="/work/a")
        self.assertEqual(sorted(self.targets("/work/a")), [])

    def test_a_relative_project_root_that_is_not_a_directory_is_refused(self) -> None:
        self.proc.add(40, APP + ["--project-root", "missing"], cwd="/work/a")
        self.assertEqual(sorted(self.targets("/work/a")), [])

    def test_without_a_project_every_recognised_process_is_selected(self) -> None:
        self.proc.add(41, ["/opt/bin/research-rag", "start"], cwd="/work/a")
        self.proc.add(42, ["/opt/bin/memory-rag", "serve"], cwd="/work/b")
        self.proc.add(43, ["/bin/sleep", "30"], cwd="/work/a")
        self.assertEqual(sorted(self.targets()), [41, 42])

    def test_a_shallowest_process_is_listed_before_the_processes_it_owns(self) -> None:
        self.proc.add(50, ["/opt/bin/research-rag", "start"])
        self.proc.add(51, GATEWAY + ["--workspace-root", "/work/a"], ppid=50)
        self.proc.add(
            52, ["/usr/bin/python3", f"{RUNTIME}/corpus/src/corpus.py"], ppid=51
        )
        self.assertEqual(sorted(self.targets()), [50, 51, 52])

    def test_only_this_account_is_considered(self) -> None:
        self.proc.add(60, ["/opt/bin/research-rag", "start"])
        mine = stops.select(proc_root=self.proc.root, uid=os.getuid())
        self.assertEqual([target.pid for target in mine], [60])
        theirs = stops.select(proc_root=self.proc.root, uid=os.getuid() + 1)
        self.assertEqual(theirs, [])

    def test_this_process_and_its_ancestors_are_never_selected(self) -> None:
        self.proc.add(os.getpid(), ["/opt/bin/research-rag", "start"], ppid=9001)
        self.proc.add(9001, ["/opt/bin/research-rag", "start"], ppid=9002)
        self.proc.add(9002, ["/opt/bin/research-rag", "start"], ppid=1)
        self.proc.add(9100, ["/opt/bin/research-rag", "start"], ppid=1)
        self.assertEqual(sorted(self.targets()), [9100])

    def test_a_zombie_has_exited_and_is_nothing_to_stop(self) -> None:
        self.proc.add(44, APP)
        self.proc.zombie(44)
        process = stops.read_process(self.proc.root, 44)
        self.assertIsNone(process)
        self.assertFalse(stops.alive(self.proc.root, 44))
        self.assertEqual(sorted(self.targets()), [])

    def test_a_snapshot_taken_across_a_reuse_is_refused(self) -> None:
        self.proc.add(45, APP)

        original = stops._argv

        def racing(directory: Path) -> tuple[str, ...]:
            # The process exits and its PID is reused while it is being read.
            self.proc.retime(45, 200)
            return original(directory)

        with mock.patch.object(stops, "_argv", racing):
            self.assertIsNone(stops.read_process(self.proc.root, 45))
        self.assertIsNotNone(stops.read_process(self.proc.root, 45))

    def test_scheduler_state_changes_do_not_change_process_identity(self) -> None:
        self.proc.add(46, APP)
        with mock.patch.object(
            stops, "_stat", side_effect=[(1, 100, "S"), (1, 100, "R")]
        ):
            process = stops.read_process(self.proc.root, 46)
        self.assertIsNotNone(process)
        self.assertEqual(process.start_time, 100)

    def test_root_directory_contains_absolute_working_directories(self) -> None:
        self.assertTrue(stops.within("/work/a", "/"))
        self.assertFalse(stops.within("/work/abc", "/work/a"))

    def test_process_arguments_preserve_non_utf8_filename_bytes(self) -> None:
        self.proc.add(47, APP)
        cmdline = self.proc.root / "47" / "cmdline"
        cmdline.write_bytes(b"research-rag\0--project-root\0/work/\xff\0")
        before = stops.read_process(self.proc.root, 47)
        cmdline.write_bytes(b"research-rag\0--project-root\0/work/\xfe\0")
        after = stops.read_process(self.proc.root, 47)
        self.assertNotEqual(before.argv, after.argv)
        self.assertEqual(os.fsencode(before.argv[-1]), b"/work/\xff")

    def test_named_project_selection_does_not_fall_back_to_cwd(self) -> None:
        project = "/work/a"
        self.proc.add(
            48, ["research-rag", "--project", "another-project", "start"], cwd=project
        )
        self.proc.add(
            49,
            ["research-rag", "mcp", "--project-name", "another-project"],
            cwd=project,
        )
        self.assertEqual(stops.select(proc_root=self.proc.root, project=project), [])


class IdentityTest(FakeProcTest):
    """No signal reaches a process that is not the one that was selected."""

    def summarise(self, targets, report):
        out, err = io.StringIO(), io.StringIO()
        code = stops.summarise(targets, report, out, err)
        return code, out.getvalue(), err.getvalue()

    def test_a_reused_pid_is_left_alone(self) -> None:
        self.proc.add(70, APP, start_time=111)
        targets = stops.select(proc_root=self.proc.root)
        self.proc.retime(70, 222)
        report, recorded, closed = self.stop(targets)
        self.assertEqual(recorded, [])
        self.assertEqual(report.signalled, [])
        self.assertEqual(report.refused, {70: stops.CHANGED})
        self.assertEqual(closed, [self.handle(70)])
        code, out, err = self.summarise(targets, report)
        self.assertEqual(code, stops.EXIT_SURVIVED)
        self.assertIn(stops.CHANGED.upper(), out)
        self.assertIn(f"left alone, {stops.CHANGED}: 70", err)

    def test_a_pid_now_running_something_else_is_left_alone(self) -> None:
        self.proc.add(71, APP)
        targets = stops.select(proc_root=self.proc.root)
        self.proc.add(71, ["/opt/bin/memory-rag", "serve"])
        report, recorded, _ = self.stop(targets)
        self.assertEqual(recorded, [])
        self.assertEqual(report.refused, {71: stops.CHANGED})

    def test_a_process_that_is_gone_is_left_alone(self) -> None:
        self.proc.add(72, APP)
        targets = stops.select(proc_root=self.proc.root)
        self.proc.forget(72)
        report, recorded, _ = self.stop(targets)
        self.assertEqual(recorded, [])
        self.assertEqual(report.signalled, [])
        self.assertEqual(report.survived, [])

    def test_a_handle_held_for_a_replacement_is_never_sent_to(self) -> None:
        self.proc.add(73, APP, start_time=111)
        targets = stops.select(proc_root=self.proc.root)
        self.proc.retime(73, 222)
        with mock.patch.object(stops.signal, "pidfd_send_signal") as sender:
            # The handle is a live value for a PID whose process has been
            # replaced, so this passes only because the identity is compared and
            # not because the PID happens to be absent.
            delivered = stops.deliver_signal(
                targets[0], signal.SIGTERM, FAKE_HANDLE, self.proc.root
            )
        self.assertFalse(delivered)
        sender.assert_not_called()

    def test_the_confirmed_process_is_sent_to(self) -> None:
        self.proc.add(73, APP, start_time=111)
        targets = stops.select(proc_root=self.proc.root)
        with mock.patch.object(stops.signal, "pidfd_send_signal") as sender:
            delivered = stops.deliver_signal(
                targets[0], signal.SIGTERM, FAKE_HANDLE, self.proc.root
            )
        self.assertTrue(delivered)
        sender.assert_called_once_with(FAKE_HANDLE, signal.SIGTERM)

    def test_a_process_with_no_handle_is_not_signalled(self) -> None:
        self.proc.add(74, APP)
        targets = stops.select(proc_root=self.proc.root)
        recorded: list[int] = []
        report = stops.stop(
            targets,
            0,
            proc_root=self.proc.root,
            open_handle=lambda pid: None,
            close_handle=lambda handle: None,
            send=lambda target, number, handle: recorded.append(target.pid) or True,
        )
        self.assertEqual(recorded, [])
        self.assertEqual(report.refused, {74: stops.NO_HANDLE})
        code, out, err = self.summarise(targets, report)
        self.assertEqual(code, stops.EXIT_NO_HANDLE)
        self.assertIn(stops.NO_HANDLE.upper(), out)
        self.assertNotIn(stops.SURVIVED_STATUS, out)
        self.assertIn("Stopped 0 of 1 process(es).", out)
        self.assertIn("refused to signal 74", err)
        self.assertIn("Linux 5.3", err)
        self.assertIn("Python 3.9", err)

    def test_a_selected_process_is_asked_and_then_forced(self) -> None:
        self.proc.add(80, ["/opt/bin/research-rag", "start"])
        self.proc.add(81, GATEWAY + ["--workspace-root", "/w"], ppid=80)
        targets = stops.select(proc_root=self.proc.root)
        report, recorded, closed = self.stop(targets)
        self.assertEqual(
            [(pid, number) for pid, number, _ in recorded],
            [
                (80, signal.SIGTERM),
                (81, signal.SIGTERM),
                (80, signal.SIGKILL),
                (81, signal.SIGKILL),
            ],
        )
        self.assertEqual(
            [handle for _, _, handle in recorded],
            [self.handle(80), self.handle(81), self.handle(80), self.handle(81)],
        )
        self.assertEqual(sorted(report.forced), [80, 81])
        self.assertEqual(sorted(report.survived), [80, 81])
        self.assertEqual(sorted(closed), [self.handle(80), self.handle(81)])
        code, out, err = self.summarise(targets, report)
        self.assertEqual(code, stops.EXIT_SURVIVED)
        self.assertIn("SURVIVED SIGTERM and SIGKILL", out)
        self.assertIn("Stopped 0 of 2 process(es).", out)
        self.assertIn("2 process(es) survived: 80 81", err)

    def test_a_process_that_answers_the_first_signal_is_not_forced(self) -> None:
        self.proc.add(82, APP)
        targets = stops.select(proc_root=self.proc.root)
        recorded: list[tuple[int, int]] = []

        def send(target: stops.Target, number: int, handle: int) -> bool:
            recorded.append((target.pid, number))
            if number == signal.SIGTERM:
                self.proc.forget(target.pid)
            return True

        report, _, _ = self.stop(targets, send=send)
        self.assertEqual(recorded, [(82, signal.SIGTERM)])
        self.assertEqual(report.survived, [])
        self.assertEqual(report.forced, [])
        code, out, err = self.summarise(targets, report)
        self.assertEqual(code, stops.EXIT_STOPPED)
        self.assertIn("Stopped 1 of 1 process(es).", out)
        self.assertEqual(err, "")

    def test_every_handle_is_closed_even_when_a_signal_raises(self) -> None:
        self.proc.add(83, APP)
        targets = stops.select(proc_root=self.proc.root)
        closed: list[int] = []

        def send(target: stops.Target, number: int, handle: int) -> bool:
            raise OSError("the sender failed")

        with self.assertRaises(OSError):
            self.stop(targets, send=send, close_handle=closed.append)
        self.assertEqual(closed, [self.handle(83)])

    def test_a_killed_process_is_not_called_a_survivor_before_it_is_reaped(
        self,
    ) -> None:
        self.proc.add(84, APP)
        targets = stops.select(proc_root=self.proc.root)
        clock = [0.0]
        looked = []

        def sleep(seconds: float) -> None:
            looked.append(seconds)
            clock[0] += seconds
            # The parent reaps it, which is what the bounded wait is for.
            self.proc.forget(84)

        left = stops.confirm_gone(targets, self.proc.root, sleep, lambda: clock[0])
        self.assertEqual(left, [])
        self.assertEqual(looked, [0.1])

    def test_a_process_still_there_after_the_wait_is_a_survivor(self) -> None:
        self.proc.add(85, APP)
        targets = stops.select(proc_root=self.proc.root)
        clock = [0.0]

        def sleep(seconds: float) -> None:
            clock[0] += seconds

        left = stops.confirm_gone(targets, self.proc.root, sleep, lambda: clock[0])
        self.assertEqual(left, [85])
        self.assertGreater(clock[0], 0.0)

    def test_the_confirmation_wait_is_bounded(self) -> None:
        self.proc.add(86, APP)
        targets = stops.select(proc_root=self.proc.root)
        slept: list[float] = []
        # A clock that never advances must not hold the run open.
        left = stops.confirm_gone(
            targets,
            self.proc.root,
            sleep=slept.append,
            monotonic=lambda: 0.0,
        )
        self.assertEqual(left, [86])
        self.assertLessEqual(len(slept), 64)


class TimeoutTest(unittest.TestCase):
    def test_whole_seconds_are_accepted(self) -> None:
        self.assertEqual(stops.timeout_seconds("0"), 0)
        self.assertEqual(stops.timeout_seconds("10"), 10)
        self.assertEqual(stops.timeout_seconds(" 30 "), 30)

    def test_anything_else_is_refused(self) -> None:
        refused = [
            "",
            "abc",
            "1.5",
            "-1",
            "10 - 5",
            "1+1",
            "$((10))",
            "$(id)",
            "`id`",
            "10; id",
            "10 && id",
            "1_000",
            "0x10",
            "9" * 5000,
            str(stops.MAX_TIMEOUT + 1),
        ]
        for value in refused:
            with self.assertRaises(argparse.ArgumentTypeError, msg=value):
                stops.timeout_seconds(value)


class CommandLineTest(unittest.TestCase):
    """The command refuses what it cannot act on."""

    def test_an_unknown_option_is_refused(self) -> None:
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as raised,
        ):
            stops.main(["--stop-everything"])
        self.assertEqual(raised.exception.code, 2)

    def test_a_timeout_that_is_not_a_number_is_refused(self) -> None:
        for value in ("5; id", "9" * 5000, "-1"):
            with (
                contextlib.redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as raised,
            ):
                stops.main(["--timeout", value])
            self.assertEqual(raised.exception.code, 2)

    def test_a_project_that_is_not_a_directory_is_refused(self) -> None:
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as raised,
        ):
            stops.main(["--project", "/nonexistent/project/root"])
        self.assertEqual(raised.exception.code, 2)

    def test_nothing_running_is_answered(self) -> None:
        out = io.StringIO()
        patch = mock.patch.object(stops, "select", return_value=[])
        with patch, contextlib.redirect_stdout(out):
            code = stops.main(["--project", str(Path(__file__).resolve().parent)])
        self.assertEqual(code, stops.EXIT_STOPPED)
        self.assertIn("No UltraRAG server processes", out.getvalue())

    def test_a_dry_run_says_so_even_when_nothing_is_running(self) -> None:
        out = io.StringIO()
        with (
            mock.patch.object(stops, "select", return_value=[]),
            mock.patch.object(stops, "stop") as stopper,
            contextlib.redirect_stdout(out),
        ):
            code = stops.main(["--dry-run"])
        self.assertEqual(code, stops.EXIT_STOPPED)
        stopper.assert_not_called()
        self.assertIn("No UltraRAG server processes", out.getvalue())
        self.assertIn("Dry run: nothing was stopped.", out.getvalue())


class DisposableProcessTest(unittest.TestCase):
    """Child processes of this test run, recognised the way a real one is."""

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.started: list[subprocess.Popen] = []

    def spawn(self, name: str, *arguments: str, cwd: str | None = None) -> int:
        """Start a sleeping process whose program token is `name`.

        The interpreter is the process's argv[0] and the program is its argv[1],
        which is the shape a console script or an UltraRAG child has, so the
        matcher sees what it sees on a running server.
        """

        program = self.root / name
        program.parent.mkdir(parents=True, exist_ok=True)
        program.write_text(SLEEPER)
        child = subprocess.Popen(
            [sys.executable, str(program), *arguments],
            executable=sys.executable,
            cwd=cwd or str(self.root),
        )
        self.started.append(child)
        self.addCleanup(self._reap, child)
        return child.pid

    def _reap(self, child: subprocess.Popen) -> None:
        if child.poll() is None:
            child.send_signal(signal.SIGKILL)
        with contextlib.suppress(subprocess.TimeoutExpired):
            child.wait(timeout=WAIT)

    def recognised(self) -> set[int]:
        return {target.pid for target in stops.select()}

    def wait_for_a_command_line(self, pids: set[int]) -> None:
        """Wait until each PID reports an argv, which a child has after its exec."""

        deadline = time.monotonic() + WAIT
        while time.monotonic() < deadline:
            if all(stops.read_process(stops.PROC_ROOT, pid) for pid in pids):
                return
            time.sleep(0.05)
        self.fail(f"no command line was reported for: {sorted(pids)}")

    def wait_for(self, pids: set[int]) -> None:
        deadline = time.monotonic() + WAIT
        while time.monotonic() < deadline:
            if pids <= self.recognised():
                return
            time.sleep(0.05)
        missing = sorted(pids - self.recognised())
        self.fail(f"not recognised among the processes: {missing}")

    def test_a_serving_app_is_recognised_and_its_project_read(self) -> None:
        project = self.root / "a project"
        project.mkdir()
        pid = self.spawn("research-rag", "--project-root", str(project), "start")
        self.wait_for({pid})
        target = next(one for one in stops.select() if one.pid == pid)
        self.assertEqual(target.role, "app")
        self.assertEqual(target.project_path, str(project.resolve()))
        chosen = [one.pid for one in stops.select(str(project.resolve()))]
        self.assertEqual(chosen, [pid])

    def test_an_account_wide_app_serving_a_project_is_not_selected_by_it(self) -> None:
        project = self.root / "a project"
        project.mkdir()
        pid = self.spawn("memory-rag", "serve")
        self.wait_for_a_command_line({pid})
        chosen = [one.pid for one in stops.select(str(project.resolve()))]
        self.assertNotIn(pid, chosen)

    def test_a_transient_app_command_is_not_recognised(self) -> None:
        project = self.root / "a project"
        project.mkdir()
        pid = self.spawn("research-rag", "--project-root", str(project), "status")
        second = self.spawn("memory-rag", "clients")
        self.wait_for_a_command_line({pid, second})
        found = self.recognised()
        self.assertNotIn(pid, found)
        self.assertNotIn(second, found)

    def test_a_sibling_directory_with_the_same_prefix_is_not_matched(self) -> None:
        first = self.root / "work" / "a"
        second = self.root / "work" / "abc"
        first.mkdir(parents=True)
        second.mkdir(parents=True)
        other = self.spawn("research-rag", "--project-root", str(second), "start")
        self.wait_for({other})
        found = {target.pid for target in stops.select(str(first.resolve()))}
        self.assertNotIn(other, found)
        chosen = [target.pid for target in stops.select(str(second.resolve()))]
        self.assertEqual(chosen, [other])

    def test_an_ultrarag_child_is_recognised(self) -> None:
        name = "vanilla-ultra-rag-mcp/runtime/abc/servers/corpus/src/corpus.py"
        pid = self.spawn(name)
        self.wait_for({pid})
        target = next(one for one in stops.select() if one.pid == pid)
        self.assertEqual(target.role, "ultrarag")

    def test_a_process_that_only_mentions_a_server_is_not_recognised(self) -> None:
        pid = self.spawn("tail", "/opt/venv/bin/research-rag")
        self.wait_for_a_command_line({pid})
        self.assertNotIn(pid, self.recognised())

    def test_this_process_is_never_a_target(self) -> None:
        self.assertNotIn(os.getpid(), self.recognised())


class PidfdTest(unittest.TestCase):
    """The identity a signal is sent through is the one that was selected."""

    def test_a_disposable_child_is_signalled_through_its_handle(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        program = Path(directory.name) / "research-rag"
        program.write_text(SLEEPER)
        child = subprocess.Popen(
            [sys.executable, str(program), "start"], executable=sys.executable
        )
        self.addCleanup(child.wait)
        process = None
        deadline = time.monotonic() + WAIT
        while process is None and time.monotonic() < deadline:
            # A child has no command line between the fork and the exec.
            process = stops.read_process(stops.PROC_ROOT, child.pid)
        self.assertIsNotNone(process, "the child never reported a command line")
        target = stops.Target(
            pid=process.pid,
            role="app",
            scope="project",
            project=None,
            cwd=None,
            start_time=process.start_time,
            argv=process.argv,
        )
        if hasattr(os, "pidfd_open") and hasattr(signal, "pidfd_send_signal"):
            self.assertIsNotNone(stops.pidfd_for(child.pid))
        report = stops.stop([target], 0)
        self.assertEqual(child.wait(timeout=WAIT), -signal.SIGTERM)
        self.assertEqual(report.survived, [])
        self.assertEqual(report.forced, [])
        self.assertEqual(report.signalled, [child.pid])
        self.assertEqual(report.refused, {})

    def test_a_child_is_left_running_when_no_handle_can_be_had(self) -> None:
        """Without a handle nothing is sent, so a process is never risked on a PID."""

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        program = Path(directory.name) / "research-rag"
        program.write_text(SLEEPER)
        child = subprocess.Popen(
            [sys.executable, str(program), "start"], executable=sys.executable
        )
        self.addCleanup(child.wait)
        self.addCleanup(child.send_signal, signal.SIGKILL)
        deadline = time.monotonic() + WAIT
        process = None
        while process is None and time.monotonic() < deadline:
            process = stops.read_process(stops.PROC_ROOT, child.pid)
        self.assertIsNotNone(process, "the child never reported a command line")
        target = stops.Target(
            pid=process.pid,
            role="app",
            scope="project",
            project=None,
            cwd=None,
            start_time=process.start_time,
            argv=process.argv,
        )
        clock = [0.0]
        report = stops.stop(
            [target],
            0,
            open_handle=lambda pid: None,
            close_handle=lambda handle: None,
            sleep=lambda seconds: clock.__setitem__(0, clock[0] + seconds),
            monotonic=lambda: clock[0],
        )
        self.assertEqual(report.signalled, [])
        self.assertEqual(report.refused, {child.pid: stops.NO_HANDLE})
        self.assertIsNone(child.poll(), "the child was signalled without a handle")


class WrapperTest(unittest.TestCase):
    """`scripts/stop-servers.sh` as a command."""

    def run_script(self, *arguments: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", str(SCRIPT), *arguments],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def test_a_dry_run_answers_and_stops_nothing(self) -> None:
        result = self.run_script("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Dry run: nothing was stopped.", result.stdout)

    def test_a_dry_run_for_a_project_answers_and_stops_nothing(self) -> None:
        result = self.run_script("--dry-run", "--project", str(REPO / "scripts"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Dry run: nothing was stopped.", result.stdout)

    def test_help_describes_the_options(self) -> None:
        result = self.run_script("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for option in ("--dry-run", "--project", "--timeout"):
            self.assertIn(option, result.stdout)

    def test_an_unknown_option_is_refused(self) -> None:
        result = self.run_script("--everything")
        self.assertEqual(result.returncode, 2)

    def test_a_timeout_that_is_not_a_number_is_refused(self) -> None:
        result = self.run_script("--timeout", "5; id")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("uid=", result.stdout)


if __name__ == "__main__":
    unittest.main()
