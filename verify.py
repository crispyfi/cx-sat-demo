#!/usr/bin/env python3
"""Run Robot Framework AOS-CX tests against devices defined in site.yaml.

Selection is mutually exclusive: --all, --device, or --persona.
Each run gets its own timestamped output directory under
``<output>/<hostname>/<YYYYMMDD-HHMMSS>/``.

Credentials are read from ``.env`` (or environment) by ``_aoscx``;
everything else flows from site.yaml through a per-device
``variables.yaml`` consumed by Robot's ``--variablefile``.
"""

import argparse
import datetime
import sys
from pathlib import Path

import yaml
from robot import run_cli


GLOBAL_RENAMES = {
    "site_name": "SITE_NAME",
    "api_version": "API_VERSION",
    "software_version": "SOFTWARE_VERSION",
}

DEVICE_RENAMES = {
    "ip": "DEVICE_IP",
}

# Per-device keys that are not exported as Robot variables.
DEVICE_SKIP = {"persona", "hostname", "serial", "part"}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Run AOS-CX Robot tests against devices in site.yaml.",
    )
    parser.add_argument(
        "-s",
        "--site",
        default="site.yaml",
        metavar="PATH",
        help="Site config YAML (default: site.yaml)",
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Run against every device in the site",
    )
    selection.add_argument(
        "-d",
        "--device",
        metavar="NAME",
        help="Run against one device (hostname or IP in site.yaml)",
    )
    selection.add_argument(
        "-p",
        "--persona",
        choices=("core", "access"),
        metavar="TYPE",
        help="Run against every device of this persona: core | access",
    )
    parser.add_argument(
        "-S",
        "--suite",
        metavar="PATTERN",
        help="Robot --suite filter",
    )
    parser.add_argument(
        "-t",
        "--test",
        metavar="PATTERN",
        help="Robot --test filter",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="output",
        metavar="DIR",
        help="Output root directory (default: output/)",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Pass --dryrun to Robot (parse only; no live calls)",
    )
    parser.add_argument(
        "-v",
        "--debug",
        action="store_true",
        help="Robot --loglevel DEBUG",
    )
    return parser.parse_args(argv)


def select_devices(site, args):
    devices = site.get("devices") or []
    if args.device:
        match = next(
            (d for d in devices if d.get("hostname") == args.device or d.get("ip") == args.device),
            None,
        )
        if not match:
            sys.exit(f"device {args.device!r} not found in {args.site}")
        return [match]
    if args.persona:
        return [d for d in devices if d.get("persona") == args.persona]
    return list(devices)  # --all


def build_variables(site, device):
    """Return the {ROBOT_NAME: value} dict for one device."""
    vars_out = {}
    for key, value in site.items():
        if key == "devices":
            continue
        robot_key = GLOBAL_RENAMES.get(key, key.upper())
        vars_out[robot_key] = value
    for key, value in device.items():
        if key in DEVICE_SKIP:
            continue
        robot_key = DEVICE_RENAMES.get(key, key.upper())
        vars_out[robot_key] = value
    # Defaults for keys that are persona-specific in site.yaml — they may be
    # absent for some devices (e.g. VSF_MEMBERS on core), but Robot tests
    # tagged for both personas still reference them as keyword arguments.
    vars_out.setdefault("VSF_MEMBERS", None)
    vars_out.setdefault("UPLINK_LAG", None)
    return vars_out


def run_one(site, device, args):
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    hostname = device.get("hostname") or device.get("ip") or "unknown"
    outdir = Path(args.output) / hostname / timestamp
    outdir.mkdir(parents=True, exist_ok=True)

    variables = build_variables(site, device)
    variables_path = outdir / "variables.yaml"
    variables_path.write_text(yaml.safe_dump(variables, sort_keys=True))

    robot_args = [
        "--variablefile",
        str(variables_path),
        "--outputdir",
        str(outdir),
        "--include",
        device["persona"],
    ]
    if args.suite:
        robot_args += ["--suite", args.suite]
    if args.test:
        robot_args += ["--test", args.test]
    if args.dry_run:
        robot_args += ["--dryrun"]
    if args.debug:
        robot_args += ["--loglevel", "DEBUG"]
    robot_args += ["tests"]

    print(f"[{hostname}] running tests → {outdir}")
    return run_cli(robot_args, exit=False)


def main(argv=None):
    args = parse_args(argv)
    site_path = Path(args.site)
    if not site_path.is_file():
        sys.exit(f"site file not found: {site_path}")
    site = yaml.safe_load(site_path.read_text())
    devices = select_devices(site, args)
    if not devices:
        sys.exit("no devices matched the selection")
    rc = 0
    for device in devices:
        rc |= run_one(site, device, args)
    return rc


if __name__ == "__main__":
    sys.exit(main())
