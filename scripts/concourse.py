import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import typer

app = typer.Typer(
    help="CLI tool for investigating Concourse CI jobs."
)


def run_command(command: list[str]) -> object:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True
    )

    return json.loads(result.stdout)


def format_utc(timestamp):
    if timestamp is None:
        return None

    return datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc
    ).strftime("%Y-%m-%d %H:%M:%S UTC")


def read_team_state_json(file_path: Path):
    with file_path.open() as f:
        return json.load(f)


def get_deploy_jobs(
    target: str,
    team: str,
    pipeline: str
):
    jobs_command = [
        "fly",
        "-t", target,
        "jobs",
        "--team", team,
        "--pipeline", pipeline,
        "--json"
    ]

    jobs = run_command(jobs_command)

    return [
        job["name"]
        for job in jobs
        if job["name"].startswith("deploy-")
    ]


def get_latest_builds_for_jobs(
    target: str,
    team: str,
    pipeline: str,
    deploy_jobs: list[str]
):
    latest_builds = []

    for job in deploy_jobs:

        builds_command = [
            "fly",
            "-t", target,
            "builds",
            "--team", team,
            "--job", f"{pipeline}/{job}",
            "--json"
        ]

        builds = run_command(builds_command)

        if builds:
            latest_builds.append(builds[0])
        else:
            latest_builds.append(None)

    return latest_builds


def build_output(
    team: str,
    application: dict,
    pipeline: str,
    job: str,
    latest_build
):
    if latest_build is None:
        return {
            "team_name": team,
            "application_name": pipeline,
            "repository": application["repository"],
            "org": application["org"],
            "pipeline_name": pipeline,
            "job_name": job,
            "build_id": None,
            "build_name": None,
            "status": None,
            "start_time_utc": None,
            "end_time_utc": None
        }

    return {
        "team_name": team,
        "application_name": pipeline,
        "repository": application["repository"],
        "org": application["org"],
        "pipeline_name": pipeline,
        "job_name": job,
        "build_id": latest_build["id"],
        "build_name": latest_build["name"],
        "status": latest_build["status"],
        "start_time_utc": format_utc(
            latest_build.get("start_time")
        ),
        "end_time_utc": format_utc(
            latest_build.get("end_time")
        )
    }


@app.command()
def investigate(
    data_file: Path = typer.Argument(
        ...,
        help="Path to the team/application JSON file."
    ),
    target: str = typer.Option(
        "ci",
        "--target",
        "-t",
        help="Concourse fly target."
    )
):
    """
    Investigate the latest deploy-* build for every application.
    """

    data = read_team_state_json(data_file)

    for team, applications in data.items():

        for application in applications:

            typer.echo("---")

            application_name = application["application_name"]
            repository = application["repository"]
            org = application["org"]

            typer.echo(
                f"Investigating team '{team}' "
                f"and application '{application_name}'"
            )

            deploy_jobs = get_deploy_jobs(
                target,
                team,
                application_name
            )

            if not deploy_jobs:
                typer.echo(
                    f"No deploy-* jobs found for "
                    f"team '{team}' and "
                    f"pipeline '{application_name}'"
                )
                continue

            latest_deploy_builds = get_latest_builds_for_jobs(
                target,
                team,
                application_name,
                deploy_jobs
            )

            for job, latest_build in zip(
                deploy_jobs,
                latest_deploy_builds
            ):

                output = build_output(
                    team=team,
                    application=application,
                    pipeline=application_name,
                    job=job,
                    latest_build=latest_build
                )

                typer.echo(
                    json.dumps(
                        output,
                        indent=4
                    )
                )



if __name__ == "__main__":
    app()