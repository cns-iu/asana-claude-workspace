# asana-claude-workspace

- `asana_report.py` pulls Asana projects listed in `projects.json` and writes snapshots to `data/` and reports to `reports/`. See README.md.
- The token comes from `ASANA_PERSONAL_ACCESS_TOKEN`, read from the environment or the gitignored `.env`. Never print it, write it anywhere else, or commit `.env`.
- `projects.json`, `data/`, and `reports/` are per-user and gitignored; `.env.example` and `projects.example.json` are the committed templates. Setup docs live in INSTALLATION.md.
- For questions about tasks, check the latest `reports/<project>/latest.md` or `data/<project>/*.json` first. Run `./run.sh` to refresh.
- Asana's read-only share links are JS-rendered, so fetching them returns no task data. Use the API.
- Keep the script dependency-free (standard library only, Python 3.9+).
- Format with black (`uvx black asana_report.py`); pass `encoding="utf-8"` to file reads and writes.
