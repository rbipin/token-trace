"""The `schedule` / `unschedule` subcommands: native OS-level daily collect job."""
from __future__ import annotations

import argparse
import platform
import subprocess
import sys

from src.schedule import (
    parse_time,
    schedule_macos,
    schedule_windows,
    unschedule_macos,
    unschedule_windows,
)


class ScheduleCommand:
    name = "schedule"
    help = "register a daily 'collect --lookback 1' job at HH:MM"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("time", help="24-hour HH:MM at which to run daily")

    def run(self, args: argparse.Namespace) -> int:
        try:
            hour, minute = parse_time(args.time)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        system = platform.system()
        try:
            if system == "Darwin":
                schedule_macos(hour, minute)
            elif system == "Windows":
                schedule_windows(hour, minute)
            else:
                print(f"Error: scheduling is not supported on {system}", file=sys.stderr)
                return 1
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        print(f"Scheduled daily 'collect --lookback 1' at {args.time}")
        return 0


class UnscheduleCommand:
    name = "unschedule"
    help = "remove the daily scheduled collect job, if any"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        pass

    def run(self, args: argparse.Namespace) -> int:
        system = platform.system()
        try:
            if system == "Darwin":
                removed = unschedule_macos()
            elif system == "Windows":
                removed = unschedule_windows()
            else:
                print(f"Error: scheduling is not supported on {system}", file=sys.stderr)
                return 1
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        if removed:
            print("Scheduled job removed")
        else:
            print("No scheduled job found")
        return 0
