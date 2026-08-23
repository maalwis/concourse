import json
import subprocess
from datetime import datetime, timezone


def run_command(command):
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


def read_team_state_json(file_path):
    with open(file_path) as f:
        return json.load(f)


def get_deploy_jobs(team, pipeline):

    jobs_command = [
        "fly",
        "-t", "ci",
        "jobs",
        "--team", team,
        "--pipeline", pipeline,
        "--json"
    ]

    jobs = run_command(jobs_command)

    deploy_jobs = [
        job["name"]
        for job in jobs
        if job["name"].startswith("deploy-")
    ]

    # print(
    #     f"Found {len(deploy_jobs)} deploy-* jobs for "
    #     f"team '{team}' and pipeline '{pipeline}'"
    # )
    # for job in deploy_jobs:
    #      print(json.dumps(job, indent=4))
        

    return deploy_jobs


def get_latest_builds_for_jobs(team, pipeline, deploy_jobs):

    latest_builds = []

    for job in deploy_jobs:

        # Get builds for this job
        builds_command = [
            "fly",
            "-t", "ci",
            "builds",
            "--team", team,
            "--job", f"{pipeline}/{job}",
            "--json"
        ]

        builds = run_command(builds_command)

        if builds:
            # Get the latest build
            latest_builds.append(builds[0])
        else:
            # No builds for this job
            latest_builds.append(None)

    # print(
    #     f"Found latest builds for {len(latest_builds)} deploy-* jobs "
    #     f"for team '{team}' and pipeline '{pipeline}'"
    # )
    # print(json.dumps(latest_builds, indent=4))

    return latest_builds


def investigate_concourse_jobs():

    data = read_team_state_json("data.json")

    for team, applications in data.items():
        for application in applications:
            print("---")   
            print(f"Investigating team '{team}' and application '{application['application_name']}'")

            repository = application["repository"]
            pipeline = application["application_name"]
            org = application["org"]

            # Get deploy-* jobs
            deploy_jobs = get_deploy_jobs(
                team,
                pipeline
            )

            if not deploy_jobs:
                print(
                    f"No deploy-* jobs found for "
                    f"team '{team}' and pipeline '{pipeline}'"
                )
                continue

            # Get latest build for every deploy-* job
            latest_deploy_builds = get_latest_builds_for_jobs(
                team,
                pipeline,
                deploy_jobs
            )

            # Process each deploy-* job and its latest build
            for job, latest_build in zip(
                deploy_jobs,
                latest_deploy_builds
            ):

                if latest_build is None:

                    output = {
                        "team_name": team,
                        "application_name": pipeline,
                        "repository": repository,
                        "org": org,
                        "pipeline_name": pipeline,
                        "job_name": job,
                        "build_id": None,
                        "build_name": None,
                        "status": None,
                        "start_time_utc": None,
                        "end_time_utc": None
                    }

                else:

                    output = {
                        "team_name": team,
                        "application_name": pipeline,
                        "repository": repository,
                        "org": org,
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

                print(json.dumps(output, indent=4))

investigate_concourse_jobs()