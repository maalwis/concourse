# Concourse CI Lab

This project is a small Concourse CI lab for learning **authentication, teams, pipelines, jobs, and CLI automation with Python**.

## Architecture

The setup uses a single administrator account and does **not** create separate users for each team.

```text
                         Concourse
                            |
                       main / owner
                            |
                         test user
                         (admin)
                            |
              +-------------+-------------+
              |                           |
        testing-team                 payment-team
          /       \                       |
         /         \                      |
    backend      frontend              payment
```

### Teams and Pipelines

| Team           | Pipelines             |
| -------------- | ---------------------- |
| `testing-team` | `backend`, `frontend` |
| `payment-team` | `payment`              |

The same `test` user is:

```text
main/owner
testing-team/owner
payment-team/owner
```

This gives the administrator access to all teams and pipelines without creating additional users.

---

## Concourse Authentication

The `main` team is the administrative team. A user with `owner` access to `main` has Concourse administrator privileges.

Authenticate from the terminal:

```bash
fly -t ci login \
  -c http://localhost:8080 \
  -n main
```

Verify:

```bash
fly -t ci status
fly -t ci userinfo
```

Expected:

```text
username  team/role
test      main/owner
```

---

## Kubernetes Port Forward

The Concourse web service is exposed locally:

```bash
kubectl port-forward svc/concourse-web 8080:8080 -n concourse
```

Then authenticate Fly against:

```text
http://localhost:8080
```

---

## Create Teams

The teams require an authorization configuration. We use the existing admin user rather than creating team-specific users.

```bash
fly -t ci set-team \
  -n testing-team \
  --local-user test
```

```bash
fly -t ci set-team \
  -n payment-team \
  --local-user test
```

Verify:

```bash
fly -t ci teams
fly -t ci userinfo
```

---

## Create Pipelines

### Backend

```bash
fly -t ci set-pipeline \
  -p backend \
  -c backend-pipeline.yml \
  --team testing-team

fly -t ci unpause-pipeline \
  -p backend \
  --team testing-team
```

### Frontend

```bash
fly -t ci set-pipeline \
  -p frontend \
  -c frontend-pipeline.yml \
  --team testing-team

fly -t ci unpause-pipeline \
  -p frontend \
  --team testing-team
```

### Payment

```bash
fly -t ci set-pipeline \
  -p payment \
  -c payment-pipeline.yml \
  --team payment-team

fly -t ci unpause-pipeline \
  -p payment \
  --team payment-team
```

---

## Pipeline Jobs

Each pipeline intentionally contains both `deploy-*` and non-deployment jobs.

### Backend

```text
build-backend
test-backend
security-scan-backend

deploy-backend-dev
deploy-backend-qa
deploy-backend-staging
deploy-backend-production
```

### Frontend

```text
build-frontend
test-frontend
lint-frontend

deploy-frontend-dev
deploy-frontend-qa
deploy-frontend-staging
deploy-frontend-production
```

### Payment

```text
build-payment
test-payment
security-scan-payment

deploy-payment-dev
deploy-payment-qa
deploy-payment-staging
deploy-payment-production
```

Total:

```text
3 pipelines
21 jobs
12 deploy-* jobs
9 non-deploy jobs
```

The non-deployment jobs are intentionally included to test the Python CLI's job filtering.

---

## Common Pipeline Resource

Each pipeline uses a time resource:

```yaml
resources:
  - name: every-minute
    type: time
    source:
      interval: 5m
```

This periodically triggers jobs for testing.

---

## Python CLI

The Python CLI reads `data.json` and uses the `fly` CLI to investigate deployment jobs.

Workflow:

```text
data.json
    |
    v
team
    |
    v
pipeline
    |
    v
fly jobs --json
    |
    v
filter deploy-*
    |
    v
fly builds --json
    |
    v
latest build
    |
    v
JSON output
```

The important filtering logic is:

```python
deploy_jobs = [
    job["name"]
    for job in jobs
    if job["name"].startswith("deploy-")
]
```

Therefore jobs such as:

```text
build-backend
test-backend
security-scan-backend
```

are ignored.

---

## Fly Commands Used by Python

Get jobs:

```bash
fly -t ci jobs \
  --team <team> \
  --pipeline <pipeline> \
  --json
```

Get builds:

```bash
fly -t ci builds \
  --team <team> \
  --job <pipeline>/<job> \
  --json
```

---

## Python Environment

The project uses **Pipenv** and **Typer**.

Install dependencies:

```bash
pipenv install
```

The project contains:

- `main.py` — main Python application
- `concourse.py` — Typer-based Concourse CLI

Both files run the **same underlying `investigate` logic**. `concourse.py` wraps it in a Typer CLI; `main.py` calls it directly as a plain Python script with no CLI layer. Use whichever entrypoint fits the context.

### Option 1: Typer CLI (`concourse.py`)

```bash
pipenv run python concourse.py
```

Since `concourse.py` has only one Typer command (`investigate`), Typer treats it as the root command — so calling the script directly, with no subcommand, runs the same logic. The explicit subcommand form still works too, since Typer keeps it registered underneath:

```bash
pipenv run python concourse.py investigate
```

Both commands above execute the exact same `investigate` logic. Use whichever you prefer; the shorter root-command form is used elsewhere in this README for brevity.

View CLI options:

```bash
pipenv run python concourse.py --help
```

### Option 2: Plain Python (`main.py`)

```bash
pipenv run python main.py
```

This runs the same `investigate` logic directly, without going through the Typer wrapper — no subcommands, no `--help`, no options parsing. It's useful for quick runs, debugging, or importing/calling the logic from other scripts without a CLI layer in the way.

---

## Useful Verification Commands

```bash
fly -t ci teams
```

```bash
fly -t ci userinfo
```

```bash
fly -t ci pipelines
```

```bash
fly -t ci jobs \
  --team testing-team \
  --pipeline backend
```

```bash
fly -t ci jobs \
  --team testing-team \
  --pipeline frontend
```

```bash
fly -t ci jobs \
  --team payment-team \
  --pipeline payment
```

---

## Key Concourse Concept

The most important distinction in this lab is:

```text
main/owner
    = Concourse administrator

team/owner
    = owner of that specific team
```

The lab uses the same `test` account for both:

```text
test
 ├── main/owner
 ├── testing-team/owner
 └── payment-team/owner
```

This provides centralized administration while keeping multiple teams and pipelines available for testing.# concourse
