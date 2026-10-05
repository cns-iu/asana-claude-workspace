# Installation

This guide sets up `asana-claude-workspace` against your own Asana account. It takes about ten minutes.
At the end you'll have a daily Markdown report of the tasks in the Asana projects you choose.

## What you need

- An Asana account that can see the projects you want to report on.
- Python 3.9 or newer (`python3 --version`). No other packages are needed.
- git, to clone the repository.
- macOS, Linux, or WSL on Windows. On plain Windows, run `python asana_report.py` instead of `./run.sh`.

## 1. Clone the repository

```bash
git clone <repository-url> asana-claude-workspace
cd asana-claude-workspace
```

## 2. Create an Asana personal access token

The script reads Asana through its API, which needs a personal access token (PAT).
A PAT is a long secret string that acts as your password for the API.

1. Sign in to Asana in your browser.
2. Open the developer console at <https://app.asana.com/0/my-apps>.
   You can also get there from Asana itself: click your profile photo (top right), choose
   **Settings**, open the **Apps** tab, and click **View developer console**.
3. Under **Personal access tokens**, click **Create new token** (or **+ New access token**).
4. Give it a name you'll recognize later, such as `asana-claude-workspace on my laptop`.
   If Asana asks you to agree to the API terms, check the box.
5. Click **Create token**.
6. **Copy the token now.** Asana shows it only once. If you lose it, delete it and create a new one.

Things to know about the token:

- **It has the same access as your account.** Anyone who has it can read and change everything
  you can see in Asana. This script only reads, but the token itself is not read-only.
- **Keep it out of git, chat, email, and screenshots.** Step 3 puts it in a `.env` file that git ignores.
- **Revoke it when you're done** or if it may have leaked: go back to the developer console and
  click **Delete** (or **Revoke**) next to the token. The script stops working until you add a new one.
- **Your organization may block PATs.** Some Asana Enterprise admins disable personal access
  tokens. If you don't see the option, or API calls fail with error 401 or 403 for a token you
  just created, ask your Asana admin.

## 3. Store the token in `.env`

Copy the example file and put your token in it:

```bash
cp .env.example .env
chmod 600 .env        # make it readable only by you
```

Open `.env` in an editor and paste the token after the `=`, with no spaces or quotes:

```
ASANA_PERSONAL_ACCESS_TOKEN=2/1234567890/1234567890123:abcdef0123456789abcdef
```

`.env` is listed in `.gitignore`, so git won't commit it. Check this with:

```bash
git status --short .env     # should print nothing
git check-ignore .env       # should print ".env"
```

If `ASANA_PERSONAL_ACCESS_TOKEN` is already set in your shell environment, that value wins
over `.env`. This is handy for CI or a cron job, but run `unset ASANA_PERSONAL_ACCESS_TOKEN`
if you want the `.env` value to be used.

## 4. Check the token and find your project IDs

Run:

```bash
./run.sh --list-projects
```

This confirms that the token works and prints every workspace and project you can see,
with their IDs (Asana calls them `gid`s):

```
Workspace: Example Org (1111111111111111)
  1209876543210987  Marketing Launch
  1201234567890123  My Action Items
```

You can also read the ID from the project's address in your browser:

- `https://app.asana.com/0/1201234567890123/list`: the ID is the number after `/0/`.
- `https://app.asana.com/1/1111111111111111/project/1201234567890123/list`: the ID is the number after `/project/`.

Asana's read-only share links (`https://app.asana.com/read-only/...`) show the workspace ID,
not the project ID, so don't take the ID from those. The script can't use share links at all,
because their content is rendered by JavaScript in the browser.

## 5. Choose your projects

Copy the example and edit it:

```bash
cp projects.example.json projects.json
```

```json
{
  "action-items": { "title": "My Action Items", "gid": "1201234567890123" },
  "launch": { "title": "Marketing Launch", "gid": "1209876543210987" }
}
```

- The key (`action-items`, `launch`) is a short name you choose. It names the folders under
  `data/` and `reports/` and is what you type to run one project (`./run.sh launch`).
  Use letters, digits, and dashes.
- `title` is the heading used in the reports.
- `gid` is the project ID from step 4, as a string in quotes.

`projects.json` is gitignored, so your project list stays private.

## 6. Run it

```bash
./run.sh
```

You should see something like:

```
Saved data/action-items/2026-10-05.json
Wrote reports/action-items/2026-10-05.md
```

Open `reports/<name>/latest.md` to read the report. See [README.md](README.md) for the other
options, such as including completed tasks or writing an activity report for a date range.

`data/` and `reports/` hold your task data and are gitignored. Don't commit them to a shared repository.

## Optional: run it every day

To refresh the reports every weekday at 7am, add a cron job (`crontab -e`) that points to your clone:

```
0 7 * * 1-5 /path/to/asana-claude-workspace/run.sh >> /path/to/asana-claude-workspace/cron.log 2>&1
```

`run.sh` changes to its own directory first, so the script finds `.env` and `projects.json`
from cron too.

## Troubleshooting

| Message | Cause and fix |
|---|---|
| `ASANA_PERSONAL_ACCESS_TOKEN is not set` | `.env` is missing, in the wrong folder, or the line is misspelled. It must sit next to `asana_report.py`. |
| `Asana API error 401 ... the token is invalid, expired, or revoked` | The token was copied incompletely, has stray spaces or quotes, or was deleted. Create a new one (step 2). Also check that an old value isn't set in your shell (`echo ${ASANA_PERSONAL_ACCESS_TOKEN:+set}`). |
| `Asana API error 403` | Your account can't access the project, or your organization blocks API tokens. |
| `Asana API error 404` | The `gid` in `projects.json` is wrong or the project isn't visible to you. Recheck it with `./run.sh --list-projects`. |
| `projects.json not found` | Do step 5. |
| `Unknown project 'x'` | The name you passed isn't a key in `projects.json`. |
| `SyntaxError` or `AttributeError: 'str' object has no attribute 'removeprefix'` | Your Python is older than 3.9. Install a newer one. |
| `python3: command not found` | Install Python 3 from <https://www.python.org/downloads/> or your package manager. |

## Removing it

Delete the token in the [developer console](https://app.asana.com/0/my-apps), then delete the folder.
