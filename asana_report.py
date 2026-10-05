#!/usr/bin/env python3
"""Snapshot Asana projects and generate Markdown reports of their tasks.

Reads the token from ASANA_PERSONAL_ACCESS_TOKEN (set in the environment or in
a .env file next to this script) and project IDs from projects.json. Standard
library only. See INSTALLATION.md for setup.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from datetime import date
from pathlib import Path

API = "https://app.asana.com/api/1.0"
ROOT = Path(__file__).resolve().parent
ENCODING = "utf-8"
TASK_FIELDS = ",".join(
    [
        "name",
        "completed",
        "completed_at",
        "created_at",
        "modified_at",
        "due_on",
        "assignee.name",
        "memberships.project.gid",
        "memberships.section.name",
        "notes",
        "permalink_url",
    ]
)


def load_dotenv(path):
    """Set KEY=VALUE pairs from a .env file, without overriding the environment."""
    if not path.exists():
        return
    for line in path.read_text(encoding=ENCODING).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


def get_token():
    load_dotenv(ROOT / ".env")
    token = os.environ.get("ASANA_PERSONAL_ACCESS_TOKEN")
    if not token:
        sys.exit(
            "ASANA_PERSONAL_ACCESS_TOKEN is not set. Copy .env.example to .env "
            "and add your token (see INSTALLATION.md)."
        )
    return token


def load_config():
    path = ROOT / "projects.json"
    if not path.exists():
        sys.exit(
            "projects.json not found. Copy projects.example.json to projects.json "
            "and add your projects (see INSTALLATION.md)."
        )
    return json.loads(path.read_text(encoding=ENCODING))


def get_all(path, params, token):
    """GET a paginated Asana collection and return every item."""
    params = dict(params, limit=100)
    items, offset = [], None
    while True:
        if offset:
            params["offset"] = offset
        url = f"{API}{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req) as resp:
                body = json.load(resp)
        except urllib.error.HTTPError as e:
            hints = {
                401: "the token is invalid, expired, or revoked",
                403: "your account can't access this resource",
                404: "the ID doesn't exist or isn't visible to you",
            }
            sys.exit(
                f"Asana API error {e.code} for {path}: "
                f"{hints.get(e.code, e.reason)}."
            )
        except urllib.error.URLError as e:
            sys.exit(f"Could not reach Asana: {e.reason}")
        items += body["data"]
        offset = (body.get("next_page") or {}).get("offset")
        if not offset:
            return items


def fetch(project_gid, token):
    sections = get_all(
        f"/projects/{project_gid}/sections", {"opt_fields": "name"}, token
    )
    tasks = get_all(
        f"/projects/{project_gid}/tasks", {"opt_fields": TASK_FIELDS}, token
    )
    return {
        "project_gid": project_gid,
        "fetched_on": date.today().isoformat(),
        "sections": [s["name"] for s in sections],
        "tasks": tasks,
    }


def list_projects(token):
    """Print every workspace and project the token can see, with their gids."""
    for ws in get_all("/workspaces", {"opt_fields": "name"}, token):
        print(f"Workspace: {ws['name']} ({ws['gid']})")
        projects = get_all(
            "/projects",
            {"workspace": ws["gid"], "archived": "false", "opt_fields": "name"},
            token,
        )
        for p in sorted(projects, key=lambda p: p["name"].lower()):
            print(f"  {p['gid']}  {p['name']}")
        print()


def section_of(task, project_gid):
    for m in task.get("memberships", []):
        if (m.get("project") or {}).get("gid") == project_gid and m.get("section"):
            return m["section"]["name"]
    return "(no section)"


def render(name, snap, include_completed=False):
    gid = snap["project_gid"]
    tasks = snap["tasks"]
    open_tasks = [t for t in tasks if not t["completed"]]
    shown = tasks if include_completed else open_tasks

    groups = OrderedDict((s, []) for s in snap["sections"])
    for t in shown:
        groups.setdefault(section_of(t, gid), []).append(t)

    lines = [
        f"# {name}: task report ({snap['fetched_on']})",
        "",
        f"Project {gid}: {len(tasks)} tasks total, "
        f"{len(tasks) - len(open_tasks)} completed, {len(open_tasks)} open.",
        "",
    ]
    for section, items in groups.items():
        if not items:
            continue
        lines += [f"## {section} ({len(items)})", ""]
        for t in items:
            box = "x" if t["completed"] else " "
            extra = [
                x
                for x in [
                    f"due {t['due_on']}" if t.get("due_on") else "",
                    (t.get("assignee") or {}).get("name", ""),
                ]
                if x
            ]
            suffix = f" ({', '.join(extra)})" if extra else ""
            lines.append(
                f"- [{box}] [{t['name'].strip()}]({t['permalink_url']}){suffix}"
            )
        lines.append("")
    return "\n".join(lines)


def in_range(timestamp, start, end):
    """True if an ISO timestamp's (UTC) date falls within [start, end]."""
    return bool(timestamp) and start <= timestamp[:10] <= end


def render_activity(name, snap, start, end):
    gid = snap["project_gid"]
    groups = OrderedDict(
        [
            ("Created and completed", []),
            ("Created, still open", []),
            ("Created earlier, completed in range", []),
            ("Other activity (modified only)", []),
        ]
    )
    for t in snap["tasks"]:
        created = in_range(t["created_at"], start, end)
        completed = t["completed"] and in_range(t.get("completed_at"), start, end)
        if created and completed:
            groups["Created and completed"].append(t)
        elif created:
            groups["Created, still open"].append(t)
        elif completed:
            groups["Created earlier, completed in range"].append(t)
        elif in_range(t["modified_at"], start, end):
            groups["Other activity (modified only)"].append(t)

    total = sum(len(items) for items in groups.values())
    lines = [
        f"# {name}: activity {start} to {end}",
        "",
        f"Project {gid}, snapshot of {snap['fetched_on']}: {total} tasks with activity "
        'in range. Dates are UTC. "Modified" is only the latest change, so tasks '
        "edited in range and again later are missed.",
        "",
    ]
    for group, items in groups.items():
        lines += [f"## {group} ({len(items)})", ""]
        if not items:
            lines += ["None.", ""]
            continue
        lines += [
            "| Created | Completed | Modified | Section | Task |",
            "|---|---|---|---|---|",
        ]
        for t in sorted(items, key=lambda t: t["created_at"]):
            done = (t.get("completed_at") or "")[:10] if t["completed"] else "open"
            title = t["name"].strip().replace("|", "\\|")
            lines.append(
                f"| {t['created_at'][:10]} | {done} | {t['modified_at'][:10]} "
                f"| {section_of(t, gid)} | [{title}]({t['permalink_url']}) |"
            )
        lines.append("")
    return "\n".join(lines)


def valid_date(value):
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a YYYY-MM-DD date: {value}") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "projects", nargs="*", help="project names from projects.json (default: all)"
    )
    parser.add_argument(
        "--all-tasks", action="store_true", help="include completed tasks in the report"
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="re-render reports from the latest saved snapshot",
    )
    parser.add_argument(
        "--list-projects",
        action="store_true",
        help="list the workspaces and projects your token can see, then exit",
    )
    parser.add_argument(
        "--from",
        dest="start",
        type=valid_date,
        metavar="YYYY-MM-DD",
        help="also write an activity report starting on this date",
    )
    parser.add_argument(
        "--to",
        dest="end",
        type=valid_date,
        metavar="YYYY-MM-DD",
        help="end date for the activity report (default: today)",
    )
    args = parser.parse_args()
    if args.end and not args.start:
        parser.error("--to requires --from")
    end = args.end or date.today().isoformat()
    if args.start and args.start > end:
        parser.error("--from must not be after --to")

    if args.list_projects:
        list_projects(get_token())
        return

    config = load_config()
    names = args.projects or list(config)
    unknown = [name for name in names if name not in config]
    if unknown:
        sys.exit(
            f"Unknown project(s): {', '.join(unknown)}. Known: {', '.join(config)}"
        )
    token = None if args.offline else get_token()

    for name in names:
        data_dir = ROOT / "data" / name
        if args.offline:
            snaps = sorted(data_dir.glob("*.json"))
            if not snaps:
                sys.exit(f"No snapshots for '{name}' in {data_dir}")
            snap = json.loads(snaps[-1].read_text(encoding=ENCODING))
        else:
            snap = fetch(config[name]["gid"], token)
            data_dir.mkdir(parents=True, exist_ok=True)
            snap_path = data_dir / f"{snap['fetched_on']}.json"
            snap_path.write_text(json.dumps(snap, indent=2) + "\n", encoding=ENCODING)
            print(f"Saved {snap_path.relative_to(ROOT)}")

        report_dir = ROOT / "reports" / name
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{snap['fetched_on']}.md"
        report = render(config[name]["title"], snap, args.all_tasks)
        report_path.write_text(report, encoding=ENCODING)
        (report_dir / "latest.md").write_text(report, encoding=ENCODING)
        print(f"Wrote {report_path.relative_to(ROOT)}")

        if args.start:
            activity_path = report_dir / f"activity-{args.start}_{end}.md"
            activity_path.write_text(
                render_activity(config[name]["title"], snap, args.start, end),
                encoding=ENCODING,
            )
            print(f"Wrote {activity_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
