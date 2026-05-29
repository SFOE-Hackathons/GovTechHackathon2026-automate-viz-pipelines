# Pipeline Blueprint
demo: demo: https://typit.in/this
## Introduction

This repository provides a blueprint for generating and uploading RDF triples — primarily in the `cube:Cube` format — to **LINDAS**. The upload process is automated using **GitHub Actions**, and several configuration options are provided that can be easily adapted for different use cases.

Each pipeline consists of two main parts:

1. **Triple generation:** Triples are created using **`pylindas`** from tabular CSV data and a metadata description.
2. **Data upload:** The generated triples are uploaded to LINDAS via a shell script executed in the CI/CD workflow.

## Triple generation

The way triples are created is not the focus of this blueprint. We present here a solution using **`pylindas`**. Other possible solutions include:

- **`barnard59`**: a powerful JavaScript solution. Needs substantial know-how
- **`sparql-generate`**: a tool close in semantics to SPARQL. Best suited for users with know-how in SPARQL
- **`ontop`**: a Java-based tool best suited to convert relational database data into triples
- **from hand**: maybe not recommended, but you can always write your triples by hand

### `pylindas`

**`pylindas`** is a Python package written to convert tabular data together with a description of the metadata into a `cube:Cube`.

To create a `cube:Cube`, a pandas DataFrame and a metadata dictionary are passed to `pylindas`. In this blueprint, the pipeline downloads CSV data from a remote endpoint and uses `inputs/metadata.yml` as the cube description. The `main.py` script orchestrates the full flow: download → validate → transform → create cube → serialize to `.ttl`.

## Local Development

### Prerequisites

- Python 3.12

### Setup

1. Create and activate a virtual environment:

```bash
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

### Running the pipeline

```bash
python main.py
```

The pipeline downloads CSV data from the Swiss government endpoint, transforms it into RDF triples, and writes the output to `outputs/cube.ttl`.

### Verifying output

After a successful run, check that the output file exists:

```bash
ls outputs/cube.ttl
```

The file should contain valid Turtle (`.ttl`) RDF data.

## Data upload

The data upload is automated via a **GitHub Actions** workflow that runs on every push to any branch.

### Workflow overview

The workflow file is located at `.github/workflows/pipeline.yml` and defines two jobs:

1. **`generate`** — Sets up Python 3.12, installs dependencies, runs `main.py`, and uploads the `outputs/` directory as a workflow artifact.
2. **`upload`** — Downloads the artifact and runs `upload.sh` to push the `.ttl` files to LINDAS.

### Branch-based environment routing

The upload job automatically selects the target environment based on the branch:

| Branch | GitHub Environment | Target |
|--------|-------------------|--------|
| `main` | PROD | Production LINDAS endpoint |
| `develop` | INT | Integration LINDAS endpoint |
| Any other branch | TEST | Test LINDAS endpoint |

### Credentials setup

Credentials are stored as secrets in **GitHub Environments**. Each environment (PROD, INT, TEST) must have the following secrets configured:

| Secret | Description |
|--------|-------------|
| `ENDPOINT_USER` | Your LINDAS username |
| `ENDPOINT_PASSWORD` | The password for your LINDAS account |
| `ENDPOINT_URL` | The LINDAS SPARQL endpoint URL |

#### Setting up GitHub Environments

1. Go to your repository on GitHub
2. Navigate to **Settings** > **Environments**
3. Create three environments: `PROD`, `INT`, and `TEST`
4. For each environment, add the secrets listed above with the appropriate values
5. Optionally, add protection rules to the `PROD` environment (e.g., required reviewers)

### Upload methods

The `upload.sh` script supports two upload methods configured via the `UPLOAD_METHOD` environment variable:

- **`PUT`** — Replaces the entire content of the target graph. Use this for regular updates where you want a clean state.
- **`POST`** — Appends data to the existing graph. Use this when accumulating data over time.

> **Note:** Don't use `PUT` for large datasets (100k+ triples) when replacing the full graph on a regular basis (daily or more often).

### How `upload.sh` works

The script:
1. Validates that all required environment variables are set
2. Finds all `.ttl` files in the output directory
3. Concatenates them into a single temporary file
4. Uploads the combined file to LINDAS via `curl` with authentication
5. Cleans up the temporary file

The workflow provides the credentials and configuration as environment variables; `upload.sh` handles the actual HTTP upload.

### Scheduled runs

You can add a schedule trigger to the workflow to run the pipeline automatically. Add a `schedule` event to the workflow file using CRON syntax:

```yaml
on:
  push:
    branches: ["*"]
  schedule:
    - cron: "0 6 * * *"  # Run daily at 06:00 UTC
```

See [Crontab.guru](https://crontab.guru/) for help with CRON expressions.


### To fix:
https://int.visualize.admin.ch/browse?previous=%7B%22order%22%3A%22SCORE%22%2C%22search%22%3A%22Schweizerische+Elektrizit%C3%A4tsbilanz+Monatswerte%22%2C%22includeDrafts%22%3Atrue%7D&dataset=https%3A%2F%2Fenergy.ld.admin.ch%2Fsfoe%2Fap%2F%2Fogd35schweizerischeelektrizitaetsbilanzmonatswerte%2F1&dataSource=Int-uncached

<img width="1841" height="714" alt="image" src="https://github.com/user-attachments/assets/247ba3bf-a13e-452e-9b89-15bb07c35e8e" />

