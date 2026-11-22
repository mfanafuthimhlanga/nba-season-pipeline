"""Write the nba_daily job definition from Databricks to deploy/nba_daily.job.json.

The job is edited in the Databricks UI; run this afterwards and commit the file,
so the schedule, task chain and retries are reviewed like code.

    python deploy/export_job.py            # uses the dbt profile "nba" for host + token

Personal details (notification e-mails, run-as user) are replaced with
placeholders: this repository is public.
"""

import json
import os
import pathlib

import yaml
from databricks.sdk import WorkspaceClient

JOB_NAME = "nba_daily"
OUT = pathlib.Path(__file__).with_name("nba_daily.job.json")


def main() -> None:
    p = yaml.safe_load(open(os.path.expanduser("~/.dbt/profiles.yml")))["nba"]["outputs"]["dev"]
    w = WorkspaceClient(host="https://" + p["host"], token=p["token"])
    job = next(j for j in w.jobs.list(name=JOB_NAME))
    settings = w.jobs.get(job.job_id).settings.as_dict()

    for key in ("email_notifications", "webhook_notifications"):
        for event, targets in (settings.get(key) or {}).items():
            if isinstance(targets, list):
                settings[key][event] = ["<owner e-mail>" for _ in targets]
    settings.pop("run_as", None)
    for t in settings.get("tasks", []):
        t.pop("email_notifications", None)
        if "warehouse_id" in (t.get("dbt_task") or {}):
            t["dbt_task"]["warehouse_id"] = "<sql warehouse id>"

    OUT.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
