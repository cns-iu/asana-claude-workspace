# asana-claude-workspace

Snapshots Asana projects through the Asana API and generates Markdown task reports.

## Setup

See [INSTALLATION.md](INSTALLATION.md) for step-by-step setup, including creating an Asana
personal access token. In short:

```bash
cp .env.example .env                        # then paste your token into .env
cp projects.example.json projects.json      # then list your projects
./run.sh --list-projects                    # check the token and find project IDs
./run.sh
```

Only Python 3.9+ is required; the script uses the standard library.
`.env`, `projects.json`, `data/`, and `reports/` are gitignored, so your token, project list,
and task data stay local.

## Usage

```bash
./run.sh                      # snapshot + report every project in projects.json
./run.sh action-items         # just one project
./run.sh --all-tasks          # include completed tasks in the report
./run.sh --offline            # re-render reports from the latest saved snapshot
./run.sh --list-projects      # list the workspaces and projects your token can see
./run.sh --from 2026-09-01 --to 2026-09-30   # also write an activity report for that range
```

An activity report groups the tasks created, completed, or modified in the range:
created and completed, created and still open, created earlier but completed in range,
and other activity (modified only). `--to` defaults to today. Dates are compared in UTC,
and because Asana only records a task's latest modification, a task edited in the range
and again afterwards won't show up as "modified only".

Output:

- `data/<project>/<YYYY-MM-DD>.json`: the raw snapshot (sections plus all tasks, including completed ones)
- `reports/<project>/<YYYY-MM-DD>.md`: the report for that day, grouped by section in board order
- `reports/<project>/latest.md`: a copy of the most recent report
- `reports/<project>/activity-<from>_<to>.md`: the activity report, when `--from` is given

Running it more than once on the same day overwrites that day's files.

## Adding a project

Add an entry to `projects.json`. Get the `gid` from `./run.sh --list-projects`, or from the
project's Asana URL (`https://app.asana.com/0/<gid>/...` or `.../project/<gid>/...`).
The read-only share links show the workspace ID, not the project ID.

```json
"my-project": { "title": "My Project", "gid": "1234567890" }
```
