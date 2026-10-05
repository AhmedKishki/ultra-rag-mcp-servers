#!/usr/bin/env python3
"""Stop this collection's own long-lived processes, matched on their real argv.

`scripts/stop-servers.sh` is the command. This module is what the command runs,
because the decisions that matter cannot be made in shell text: a process is read
from the NUL-separated argv in `/proc`, and an argument that merely mentions an
entry point is not a program.

Signalling is fail-closed. A process is reached through a pidfd, which names one
process for as long as it stays open, so a PID reused between the snapshot and
the signal cannot be signalled in its place. Where no pidfd is available nothing
is signalled and the run says why, because a PID on its own cannot be signalled
safely. Signalling therefore needs Linux 5.3 or newer and Python 3.9 or newer;
`--dry-run` and every refusal below work on anything older.

Every process is read from a `proc_root` given by the caller, and every handle
and signal is injected, so this is testable against a synthetic snapshot and
against disposable child processes without stopping anything that is running.
"""

from __future__ import annotations

import argparse
import os
import re
import signal
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

PROC_ROOT = Path("/proc")
MAX_TIMEOUT = 3600
#: How long a SIGKILL is given to be seen before a process is called a survivor,
#: because a killed process stays visible until it is reaped.
CONFIRM_SECONDS = 2.0
#: Why a process was not signalled: no handle to it could be had, or it is no
#: longer the process that was selected, or both signals were ignored.
NO_HANDLE = "no signal handle"
CHANGED = "no longer the process that was selected"
SURVIVED = "survived SIGTERM and SIGKILL"
SURVIVED_STATUS = "SURVIVED SIGTERM and SIGKILL"

#: What the command answers. A refused command line is argparse's own exit 2.
EXIT_STOPPED = 0
EXIT_SURVIVED = 1
EXIT_NO_HANDLE = 3

#: Console scripts this collection owns, and the role each has. The match is the
#: whole basename of the program token, so a file carrying the name in one of its
#: arguments is not one of these. The entry points that answer and exit are
#: deliberately absent, because a command that answers is not something to stop:
#: `research-rag-runtime`, which `doctor --repair-runtime` calls, and
#: `memory-ultra-rag-reindex`.
SERVER_SCRIPTS = {
    "graph-memory-ultra-rag-mcp": "server",
    "memory-ultra-rag-mcp": "server",
    "memory-ultra-rag-ui": "ui",
    "research-rag-gateway": "gateway",
    "research-ultra-rag-mcp": "server",
    "research-ultra-rag-ui": "ui",
    "research-ultra-rag-verify": "verify",
    "vanilla-ultra-rag-mcp": "gateway",
    "vanilla-ultra-rag-runtime": "server",
    "vanilla-ultra-rag-ui": "ui",
}
SERVER_MODULES = {
    "graph_memory_ultra_rag_mcp": "server",
    "memory_ultra_rag_mcp": "server",
    "research_ultra_rag_mcp": "server",
    "vanilla_ultra_rag_mcp": "gateway",
}
#: The memory app is one process for the account rather than one per project, so
#: a project never selects it: stopping an account app to serve one project
#: would take every other project with it.
ACCOUNT_WIDE = frozenset({"memory-rag", "memory_rag"})
#: The two apps' console scripts, with the subcommands that keep a process alive.
#: A command that answers and exits is not in the set, so `research-rag status`,
#: `research-rag config`, `memory-rag clients` and `memory-rag sql` are never
#: stopped.
APP_COMMANDS = {
    "memory-rag": frozenset({"mcp", "serve"}),
    "research-rag": frozenset({"mcp", "start"}),
}
#: The apps' module names, which are the console script names with a dash. The
#: launcher starts the memory app as `python -m memory_rag`.
APP_MODULES = {"memory_rag": "memory-rag", "research_rag": "research-rag"}
#: `research-rag` serves the project when it is given no command at all, which is
#: how its workspace is brought up. A bare `memory-rag` prints its menu and
#: exits, so it is not in this set.
BARE_SERVES = frozenset({"research-rag"})
#: Flags that make an app answer and exit rather than serve.
TERMINAL_FLAGS = frozenset({"--help", "--version", "-h"})
#: Options of the two apps that carry a value, which is a path or a name and so
#: is not the subcommand that follows it.
VALUE_OPTIONS = frozenset(
    {
        "--config",
        "--model-cache-root",
        "--port",
        "--project",
        "--project-root",
        "--runtime-cache-root",
        "--runtime-root",
        "--set",
        "--storage-root",
    }
)
#: Interpreter flags that carry no value, so the script after them is still the
#: program. Any other flag ends the reading instead of naming a program out of a
#: value, an option argument, code, or standard input.
INTERPRETER_FLAGS = frozenset(
    {"-B", "-E", "-I", "-O", "-OO", "-P", "-R", "-S", "-b", "-bb", "-s", "-u"}
)
#: The options that name a project directory. A gateway is given the working
#: directory inside the project's own derived state, which names the project.
PROJECT_OPTIONS = ("--project-root", "--workspace-root")
PROJECT_STATE = "/.research-rag/"
INTERPRETER = re.compile(r"python(?:[0-9]+(?:\.[0-9]+)*)?\Z")
#: UltraRAG's own stages, which the gateway starts as scripts under its managed
#: runtime cache and which live as long as the gateway does.
RUNTIME_CHILD = re.compile(
    r"(?:\A|/)vanilla-ultra-rag-mcp/runtime/[^/]+/servers/"
    r"(?P<stage>corpus|retriever)/src/(?P=stage)\.py\Z"
)
#: A timeout is digits and nothing else, so nothing a caller passes is ever
#: evaluated. The length is bounded too, because an enormous integer is refused
#: by the interpreter before it is compared with the longest timeout.
TIMEOUT = re.compile(r"[0-9]+\Z")
MAX_TIMEOUT_DIGITS = len(str(MAX_TIMEOUT))


@dataclass(frozen=True)
class Process:
    """One process, read from the snapshot rather than from `ps` output."""

    pid: int
    ppid: int
    uid: int
    start_time: int
    argv: tuple[str, ...]
    cwd: str | None


@dataclass(frozen=True)
class NamedPath:
    """A path an invocation named, with the option that named it.

    The value is kept as it was written. A relative path means a different
    directory in every process, so it is resolved against the directory that
    process runs in and never on its own.
    """

    option: str
    value: str


@dataclass(frozen=True)
class Target:
    """A recognised process, with what was decided about it."""

    pid: int
    role: str
    scope: str
    project: NamedPath | None
    cwd: str | None
    start_time: int
    argv: tuple[str, ...]
    depth: int = 0

    @property
    def project_path(self) -> str | None:
        """The project this invocation names, as far as it can be read."""

        if self.project is None:
            return None
        if self.project.option == "--workspace-root":
            return self.project.value.split(PROJECT_STATE, 1)[0] or None
        return self.project.value


@dataclass
class Report:
    """What a stop did, and what it declined to do."""

    signalled: list[int] = field(default_factory=list)
    forced: list[int] = field(default_factory=list)
    survived: list[int] = field(default_factory=list)
    refused: dict[int, str] = field(default_factory=dict)


def _argv(directory: Path) -> tuple[str, ...]:
    """The argv in `/proc`, split on the NUL that separates its arguments."""

    raw = (directory / "cmdline").read_bytes()
    return tuple(os.fsdecode(part) for part in raw.split(b"\0") if part)


def _stat(directory: Path) -> tuple[int, int, str] | None:
    """`ppid`, `starttime` and `state`, counted from the end of `comm`.

    `comm` is parenthesised and may hold spaces and parentheses, so the fields
    after it are counted from its closing parenthesis: `state` is field 3, `ppid`
    field 4, and `starttime` field 22.
    """

    try:
        raw = (directory / "stat").read_text("utf-8", "replace")
        fields = raw[raw.rindex(")") + 1 :].split()
        return int(fields[1]), int(fields[19]), fields[0]
    except (OSError, IndexError, ValueError):
        return None


def read_process(proc_root: Path, pid: int) -> Process | None:
    """One process, or `None` when it is gone, unreadable, or a zombie.

    `stat` is read before and after `cmdline` and the two readings must agree,
    because a process that exits and whose PID is reused while it is being read
    would otherwise be described with the next process's arguments. The start
    time is what says whether two readings are of one process.

    A zombie has exited and is waiting to be reaped, so it is not running and is
    reported as gone. A kernel thread has no argv and cannot be recognised by a
    program.
    """

    directory = proc_root / str(pid)
    try:
        before = _stat(directory)
        argv = _argv(directory)
        after = _stat(directory)
        uid = directory.stat().st_uid
    except OSError:
        return None
    if before is None or after is None or before[:2] != after[:2] or not argv:
        return None
    ppid, start_time, state = after
    if state == "Z":
        return None
    try:
        cwd: str | None = os.readlink(directory / "cwd")
    except OSError:
        cwd = None
    return Process(pid, ppid, uid, start_time, argv, cwd)


def program_of(argv: Sequence[str]) -> tuple[str, tuple[str, ...]] | None:
    """The token naming the program being run, and the arguments after it.

    A console script passes its own path, so argv[0] is the program. An
    interpreter passes a script or `-m module` after itself, and only a flag
    known to carry no value is stepped over: any other flag ends the reading,
    because `-c` carries code rather than a script, `-` reads a program from
    standard input, and a flag with a value would leave that value to be taken
    for a filename. `env` passes its assignments first and the program next.
    """

    if not argv:
        return None
    index = 0
    name = os.path.basename(argv[0])
    if INTERPRETER.fullmatch(name):
        index = 1
        while index < len(argv):
            token = argv[index]
            if token == "-m":
                if index + 1 >= len(argv):
                    return None
                return argv[index + 1], tuple(argv[index + 2 :])
            if token in INTERPRETER_FLAGS:
                index += 1
                continue
            if token.startswith("-"):
                return None
            break
        if index >= len(argv):
            return None
    elif name == "env":
        index = 1
        while (
            index < len(argv) and "=" in argv[index] and not argv[index].startswith("-")
        ):
            index += 1
        if index >= len(argv) or argv[index].startswith("-"):
            return None
    if index >= len(argv):
        return None
    return argv[index], tuple(argv[index + 1 :])


def subcommand_of(arguments: Sequence[str]) -> str | None:
    """The first argument that is a command rather than an option or its value."""

    skip = False
    for token in arguments:
        if skip:
            skip = False
            continue
        if token.startswith("-") and token != "-":
            skip = "=" not in token and token in VALUE_OPTIONS
            continue
        return token
    return None


def classify(program: str, arguments: Sequence[str]) -> str | None:
    """The role of the program, or `None` when this process is not to be stopped.

    A console script or module of this collection is recognised by its own name.
    The apps are recognised only in the invocations that keep a process alive.
    """

    if RUNTIME_CHILD.search(program):
        return "ultrarag"
    # A console script passes its own path, so the name compared here is the last
    # component of it, and a module passes the module's own name.
    name = os.path.basename(program)
    role = SERVER_SCRIPTS.get(name)
    if role is not None:
        return role
    role = SERVER_MODULES.get(name)
    if role is not None:
        return role
    script = APP_MODULES.get(name, name)
    commands = APP_COMMANDS.get(script)
    if commands is None:
        return None
    if any(flag in arguments for flag in TERMINAL_FLAGS):
        return None
    subcommand = subcommand_of(arguments)
    if subcommand is None:
        return "app" if script in BARE_SERVES else None
    return "app" if subcommand in commands else None


def scope_of(program: str) -> str:
    """Whether the program serves one project or the whole account."""

    return "account" if os.path.basename(program) in ACCOUNT_WIDE else "project"


def named_project(arguments: Sequence[str]) -> NamedPath | None:
    """The project directory this invocation names, read as whole arguments.

    `--project-root /x` and `--project-root=/x` are one value, and a value with a
    space in it is that value.
    """

    for index, token in enumerate(arguments):
        for option in PROJECT_OPTIONS:
            if token == option and index + 1 < len(arguments):
                return NamedPath(option, arguments[index + 1])
            if token.startswith(f"{option}="):
                return NamedPath(option, token.split("=", 1)[1])
    return None


def within(path: str, project: str) -> bool:
    """Whether a path is the project itself or a directory inside it."""

    return path == project or path.startswith(f"{project.rstrip('/')}/")


def same_path(value: str, project: str) -> bool:
    """Whether two paths name one directory, resolving a path that exists."""

    if value == project:
        return True
    try:
        return Path(value).resolve() == Path(project)
    except OSError:
        return False


def names_project(target: Target, project: str) -> bool | None:
    """Whether an invocation names this project.

    `True` and `False` are answers. `None` says the invocation names a project
    but the path cannot be resolved: it is relative and the process's own
    directory is unknown, or the result is not a directory. Such a process is
    never selected on a guess, and never on its directory either.
    """

    named = target.project
    if named is None:
        return None
    value = target.project_path or ""
    if not value:
        return False
    if value.startswith("/"):
        return same_path(value, project)
    if not target.cwd:
        return None
    resolved = os.path.normpath(os.path.join(target.cwd, value))
    return same_path(resolved, project) if Path(resolved).is_dir() else None


def ancestor_pids(proc_root: Path = PROC_ROOT) -> set[int]:
    """This process and every process that started it, which are never stopped.

    A terminal, the shell in it, and the session leader that owns them are
    ancestors of a stop, and a stop that reached one of them would take the
    operator's session with it.
    """

    found: set[int] = set()
    pid = os.getpid()
    while pid and pid not in found:
        found.add(pid)
        process = read_process(proc_root, pid)
        if process is None:
            break
        pid = process.ppid
    return found


def select(
    project: str | None = None,
    *,
    proc_root: Path = PROC_ROOT,
    uid: int | None = None,
    excluded: Iterable[int] | None = None,
) -> list[Target]:
    """Every process of this account that is one of ours to stop.

    Without a project, that is every recognised process. With one, it is the
    processes that name that project and the recognised processes beneath them,
    so a gateway and the UltraRAG children it started come with the app that
    named the project.

    A process that names no project at all is selected by the directory it runs
    in, because that is how an app given no project root finds one. A process
    that names a different project is not, and neither is one for which the named
    path cannot be resolved. An account-wide app is never selected by a project,
    because it is not one project's process.
    """

    owner = os.getuid() if uid is None else uid
    skip = set(ancestor_pids(proc_root))
    if excluded:
        skip.update(excluded)

    processes: dict[int, Process] = {}
    try:
        entries = sorted(
            int(entry.name) for entry in proc_root.iterdir() if entry.name.isdigit()
        )
    except OSError:
        return []
    for pid in entries:
        if pid in skip:
            continue
        process = read_process(proc_root, pid)
        if process is None or process.uid != owner:
            continue
        processes[pid] = process

    candidates: dict[int, Target] = {}
    for pid, process in processes.items():
        found = program_of(process.argv)
        if found is None:
            continue
        program, arguments = found
        role = classify(program, arguments)
        if role is None:
            continue
        candidates[pid] = Target(
            pid=pid,
            role=role,
            scope=scope_of(program),
            project=named_project(arguments),
            cwd=process.cwd,
            start_time=process.start_time,
            argv=process.argv,
        )

    if project is None:
        keep = list(candidates.values())
    else:
        roots = {
            target.pid for target in candidates.values() if is_root(target, project)
        }
        keep = [
            target
            for target in candidates.values()
            if target.pid in roots or descendant_of(target.pid, roots, processes)
        ]
    return order(keep, processes)


def is_root(target: Target, project: str) -> bool:
    """Whether a process serves this project and its family follows from it."""

    if target.scope == "account":
        return False
    if target.project is None and any(
        argument in {"--project", "--project-name"}
        or argument.startswith(("--project=", "--project-name="))
        for argument in target.argv
    ):
        # A registered name can point elsewhere; cwd does not prove its identity.
        return False
    match = names_project(target, project)
    if match is not None:
        return match
    return bool(target.project is None and target.cwd and within(target.cwd, project))


def descendant_of(pid: int, roots: set[int], processes: dict[int, Process]) -> bool:
    """Whether a process sits beneath one of the selected roots."""

    probe, hops = pid, 0
    while hops < 64:
        process = processes.get(probe)
        if process is None or process.ppid == 0:
            return False
        probe = process.ppid
        if probe in roots:
            return True
        hops += 1
    return False


def depth_of(pid: int, keep: set[int], processes: dict[int, Process]) -> int:
    """How far a process sits below the nearest process also being stopped.

    A top-level server is zero and anything it owns is one deeper, so a server
    is always signalled before the processes it owns.
    """

    depth, probe, hops = 0, pid, 0
    while hops < 64:
        process = processes.get(probe)
        if process is None or process.ppid == 0 or process.ppid not in keep:
            break
        depth += 1
        probe = process.ppid
        hops += 1
    return depth


def order(targets: Sequence[Target], processes: dict[int, Process]) -> list[Target]:
    """The targets shallowest first, and by PID within a depth, which is stable."""

    keep = {target.pid for target in targets}
    depths = {target.pid: depth_of(target.pid, keep, processes) for target in targets}
    return [
        replace(target, depth=depths[target.pid])
        for target in sorted(targets, key=lambda one: (depths[one.pid], one.pid))
    ]


def unchanged(proc_root: Path, target: Target) -> bool:
    """Whether the PID still holds the process the snapshot recorded.

    The argv and the start time are compared together, and both must be readable:
    a process that cannot be read is not confirmed, so nothing is signalled
    through its PID.
    """

    process = read_process(proc_root, target.pid)
    if process is None:
        return False
    return process.start_time == target.start_time and process.argv == target.argv


def pidfd_for(pid: int) -> int | None:
    """A handle on this exact process, or `None` where the kernel gives none.

    A pidfd names one process for as long as it is open, so a signal sent
    through it reaches that process or reaches nothing, and it can never reach a
    process that later reused the PID. Linux 5.3 and Python 3.9 introduced the
    two calls this needs.
    """

    if not hasattr(os, "pidfd_open") or not hasattr(signal, "pidfd_send_signal"):
        return None
    try:
        return os.pidfd_open(pid)
    except OSError:
        return None


def deliver_signal(
    target: Target,
    number: int,
    handle: int,
    proc_root: Path = PROC_ROOT,
) -> bool:
    """Signal one process through its handle, once it is confirmed to be that one.

    The identity is compared after the handle was taken and before every signal,
    so a handle opened for a PID whose process had already been replaced is never
    sent to. A handle the kernel would not give is a refusal rather than a reason
    to signal by PID, because the PID is what reuse makes unsafe.
    """

    if not unchanged(proc_root, target):
        return False
    try:
        signal.pidfd_send_signal(handle, number)
    except OSError:
        return False
    return True


def survivors(targets: Sequence[Target], proc_root: Path) -> list[Target]:
    """The targets still running."""

    return [target for target in targets if alive(proc_root, target.pid)]


def alive(proc_root: Path, pid: int) -> bool:
    """Whether a PID still names a running process. A zombie has exited."""

    return read_process(proc_root, pid) is not None


def confirm_gone(
    targets: Sequence[Target],
    proc_root: Path,
    sleep: Callable[[float], None],
    monotonic: Callable[[], float],
    window: float = CONFIRM_SECONDS,
) -> list[int]:
    """Wait a bounded while for the survivors to be seen gone, and report those left.

    A killed process is still readable until its parent reaps it, so a check
    made immediately after SIGKILL reports processes that have already exited.
    The wait is bounded in both time and in how many times it looks, so a clock
    that does not advance cannot hold the run open.
    """

    deadline = monotonic() + window
    for _ in range(64):
        left = survivors(targets, proc_root)
        if not left or monotonic() >= deadline:
            return [target.pid for target in left]
        sleep(0.1)
    return [target.pid for target in survivors(targets, proc_root)]


def stop(
    targets: Sequence[Target],
    timeout: int,
    *,
    proc_root: Path = PROC_ROOT,
    send: Callable[[Target, int, int], bool] | None = None,
    open_handle: Callable[[int], int | None] = pidfd_for,
    close_handle: Callable[[int], None] = os.close,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> Report:
    """Ask every target to stop, then insist on the ones that ignored it.

    A handle is taken on each process before the first signal and closed when the
    run ends, however it ends. A target with no handle is left running and named,
    because there is no way to reach one process rather than another without one.
    """

    report = Report()
    handles: dict[int, int | None] = {}

    def deliver(target: Target, number: int, handle: int) -> bool:
        if send is not None:
            return send(target, number, handle)
        return deliver_signal(target, number, handle, proc_root)

    try:
        for target in targets:
            handles[target.pid] = open_handle(target.pid)
        for number in (signal.SIGTERM, signal.SIGKILL):
            pending = (
                targets if number == signal.SIGTERM else survivors(targets, proc_root)
            )
            for target in pending:
                handle = handles.get(target.pid)
                if handle is None:
                    if alive(proc_root, target.pid):
                        report.refused.setdefault(target.pid, NO_HANDLE)
                    continue
                # The identity is confirmed here and again inside the delivery,
                # before every signal, so neither the seam a caller injects nor a
                # handle opened for a PID that has since been reused can send to
                # a process that is not this one.
                if not unchanged(proc_root, target):
                    report.refused.setdefault(target.pid, CHANGED)
                    continue
                if deliver(target, number, handle):
                    report.signalled.append(target.pid)
                    if number == signal.SIGKILL:
                        report.forced.append(target.pid)
            if number == signal.SIGKILL or not pending:
                break
            deadline = monotonic() + timeout
            while monotonic() < deadline and survivors(targets, proc_root):
                sleep(0.1)
        report.survived = confirm_gone(targets, proc_root, sleep, monotonic)
        for pid in report.survived:
            report.refused.setdefault(pid, SURVIVED)
    finally:
        for handle in handles.values():
            if handle is not None:
                close_handle(handle)
    return report


def timeout_seconds(text: str) -> int:
    """A timeout as whole seconds.

    The value is only ever digits, so nothing in it is evaluated. A caller that
    passes an expression, a command, a fraction, a negative number, or more digits
    than the longest timeout has is told what a timeout may be.
    """

    value = text.strip()
    if not TIMEOUT.match(value) or len(value) > MAX_TIMEOUT_DIGITS:
        raise argparse.ArgumentTypeError(
            f"timeout must be whole seconds up to {MAX_TIMEOUT}, not {text!r}"
        )
    seconds = int(value)
    if seconds > MAX_TIMEOUT:
        raise argparse.ArgumentTypeError(
            f"timeout must be at most {MAX_TIMEOUT} seconds"
        )
    return seconds


def project_path(text: str) -> str:
    """A project directory, resolved so a path is compared with its real form."""

    path = Path(text).expanduser()
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"project path not found: {text}")
    return str(path.resolve())


def report_table(targets: Sequence[Target], project: str | None, out) -> None:
    """The plan, before anything is signalled."""

    print(
        f"Found {len(targets)} process(es){f' for {project}' if project else ''}:",
        file=out,
    )
    print(f"  {'PID':<8} {'ROLE':<9} {'DEPTH':<10} PROJECT", file=out)
    for target in targets:
        print(
            f"  {target.pid:<8} {target.role:<9} {target.depth:<10} "
            f"{target.project_path or '-'}",
            file=out,
        )


def summarise(targets: Sequence[Target], report: Report, out, err) -> int:
    """Print what a stop did, and answer with the exit code it means.

    A process that has gone counts as stopped: nothing is left running that this
    run chose. A process that ignored both signals, or that was never reachable,
    is still running, so it is named and the answer is a failure.
    """

    for target in targets:
        if target.pid in report.survived:
            why = report.refused.get(target.pid, SURVIVED)
            row = f"  {target.pid:<8} {target.role:<9} {target.depth:<10} "
            print(row + (SURVIVED_STATUS if why == SURVIVED else why.upper()), file=out)
    unreachable = sorted(pid for pid, why in report.refused.items() if why == NO_HANDLE)
    changed = sorted(pid for pid, why in report.refused.items() if why == CHANGED)
    unfinished = set(report.survived) | set(unreachable)
    print(
        f"\nStopped {len(targets) - len(unfinished)} of {len(targets)} process(es).",
        file=out,
    )
    if changed:
        left = " ".join(str(pid) for pid in changed)
        print(f"stop-servers.sh: left alone, {CHANGED}: {left}", file=err)
    if unreachable:
        left = " ".join(str(pid) for pid in unreachable)
        print(
            f"stop-servers.sh: refused to signal {left}: no handle to the process "
            f"could be had, which needs Linux 5.3 or newer and Python 3.9 or newer. "
            f"Nothing was sent to them, and they are still running.",
            file=err,
        )
    if unreachable:
        return EXIT_NO_HANDLE
    if report.survived:
        left = " ".join(str(pid) for pid in report.survived)
        print(
            f"stop-servers.sh: {len(report.survived)} process(es) survived: {left}",
            file=err,
        )
        return EXIT_SURVIVED
    return EXIT_STOPPED


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stop-servers.sh",
        description=(
            "Stop this collection's servers, gateways, and the UltraRAG children "
            "they started. Each is named by its own entry point, never by a "
            "pattern, and each is reached through a handle on that one process."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list what would be stopped and stop nothing",
    )
    parser.add_argument(
        "--project",
        type=project_path,
        metavar="PATH",
        help="only the processes serving this project",
    )
    parser.add_argument(
        "--timeout",
        type=timeout_seconds,
        metavar="SECONDS",
        default=10,
        help="seconds to wait after SIGTERM before SIGKILL (default 10)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one stop, and answer with what it did."""

    arguments = build_parser().parse_args(argv)
    targets = select(arguments.project)
    if targets:
        report_table(targets, arguments.project, sys.stdout)
    elif arguments.project:
        print(f"No UltraRAG server processes are running for {arguments.project}.")
    else:
        print("No UltraRAG server processes are running.")
    if arguments.dry_run:
        print("\nDry run: nothing was stopped.")
        return EXIT_STOPPED
    if not targets:
        return EXIT_STOPPED
    return summarise(targets, stop(targets, arguments.timeout), sys.stdout, sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
