# Pipeline Blueprint
demo: https://typit.in/this

## Introduction

This repository provides a blueprint for generating and uploading RDF triples — primarily in the `cube:Cube` format — to **LINDAS**. The upload process is automated using **GitHub Actions**, and several configuration options are provided that can be easily adapted for different use cases.

Each pipeline consists of two main parts:

1. **Triple generation:** Triples are created using **`pylindas`** from tabular CSV data and a metadata description.
2. **Data upload:** The generated triples are uploaded to LINDAS via a shell script executed in the CI/CD workflow.

## Why Long Format (Wide vs. Long)

When publishing data on [visualize.admin.ch](https://visualize.admin.ch), the structure of your DataFrame determines what visualizations are possible.

**Wide format** (one column per measure) limits you to separate chart lines — you cannot segment or stack values within a single chart.

**Long format** (categorical column + value column) enables segmentation features like **stacked bar charts**. For example, if you want to display different energy generation types (Laufwerk, Speicherwerk, Kernkraftwerk, etc.) as a stacked bar chart on visualize.admin.ch, the generation types must be stored as values in a single categorical column (e.g., `erzeugungstyp`) defined as a **Key Dimension** in the metadata.

```
Wide format (limited visualization):
| datum      | laufwerk_gwh | speicherwerk_gwh | kernkraftwerk_gwh |
|------------|--------------|------------------|-------------------|

Long format (enables stacked bar charts):
| datum      | erzeugungstyp | gwh |
|------------|---------------|-----|
| 2024-01-01 | Laufwerk      | 250 |
| 2024-01-01 | Speicherwerk  | 180 |
| 2024-01-01 | Kernkraftwerk | 200 |
```

Use `pd.melt()` in your transform function to convert wide to long format.

## Triple Generation with `pylindas`

**`pylindas`** is a Python package that converts tabular data together with a metadata description into a `cube:Cube`.

To create a `cube:Cube`, a pandas DataFrame and a metadata dictionary are passed to `pylindas`. In this blueprint, the pipeline downloads CSV data from a remote endpoint and uses `inputs/metadata.yml` as the cube description. The `main.py` script orchestrates the full flow: download → validate → transform → create cube → serialize to `.ttl`.

### Other tools for triple generation

- **`barnard59`**: a powerful JavaScript solution. Needs substantial know-how
- **`sparql-generate`**: a tool close in semantics to SPARQL. Best suited for users with know-how in SPARQL
- **`ontop`**: a Java-based tool best suited to convert relational database data into triples
- **from hand**: maybe not recommended, but you can always write your triples by hand

## Metadata Configuration (`inputs/metadata.yml`)

The `metadata.yml` file describes your dataset and its dimensions for `pylindas`. It controls how the RDF cube is structured and how it appears on visualize.admin.ch.

### General Structure

```yaml
Name:
  de: German name
  en: English name
  fr: French name
  it: Italian name

Description:
  de: German description
  en: English description
  fr: French description
  it: Italian description

Publisher:
  - IRI: https://register.ld.admin.ch/opendataswiss/org/your-org

Creator:
  - IRI: https://register.ld.admin.ch/opendataswiss/org/your-org

Contributor:
  - IRI: https://register.ld.admin.ch/opendataswiss/org/your-org
    Name: Your Organization Name

Date Created: 2024-01-15  # ISO date format

Contact Point:
  E-Mail: shared-mailbox@example.ch  # Use a shared mailbox, not personal
  Name: Your Team Name

Base-URI: https://energy.ld.admin.ch/your-namespace  # Ask BAR if unsure
Identifier: your-unique-dataset-id  # Must be unique across LINDAS
Version: 1  # Numeric, increment on breaking changes

Work Status: Draft  # Draft or Published
Visualize: true  # true = visible on visualize.admin.ch

Accrual Periodicity: monthly  # How often data is updated

Namespace:  # Optional, makes TTL more readable

dimensions:
  # One entry per column in your DataFrame
  your_column_name:
    name:
      de: ...
      fr: ...
      it: ...
      en: ...
    description:
      de: ...
      fr: ...
      it: ...
      en: ...
    dimension-type: Key Dimension  # see below
    datatype: xsd:date  # XSD vocabulary
    scale-type: ordinal  # nominal, ordinal, interval, ratio
    path: your_column  # URI path for the predicate
    unit:  # Unit of measurement (e.g., GWh, month)
    data-kind:
      type:  # temporal or spatial
      unit:  # unit if temporal
    mapping:
      type:  # additive or replacement
      base:  # for additive
      mappings:  # for replacement
```

### Dimension Types

| Type | Purpose | Example |
|------|---------|---------|
| **Key Dimension** | Part of the observation's composite key. Identifies unique observations. | `datum`, `erzeugungstyp` |
| **Measure Dimension** | The observed numeric value. | `gwh` |
| **Standard Dimension** | Additional context, not part of the key. | `definitiv` |
| **Annotation** | Metadata attached to observations. | Comments, notes |

### Important Rules

- The **key** of each dimension entry must exactly match the column name in your DataFrame (lowercase)
- Every column in your DataFrame needs a corresponding dimension entry
- At least one **Key Dimension** and one **Measure Dimension** are required
- For segmentation/stacking on visualize.admin.ch, the categorical column must be a **Key Dimension**
- `datatype` uses XSD vocabulary: `xsd:date`, `xsd:string`, `xsd:integer`, `xsd:decimal`, etc.
- `scale-type` determines how the data can be aggregated: `nominal` (categories), `ordinal` (ordered), `interval`, `ratio` (numeric with true zero)

### Example: Long Format for Stacked Charts

To enable stacked bar charts by generation type on visualize.admin.ch:

```yaml
dimensions:
  datum:
    dimension-type: Key Dimension
    datatype: xsd:date
    scale-type: ordinal

  erzeugungstyp:
    dimension-type: Key Dimension  # Must be Key Dimension for segmentation!
    datatype: xsd:string
    scale-type: nominal

  gwh:
    dimension-type: Measure Dimension
    datatype: xsd:integer
    scale-type: ratio
    unit: GWh
```

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

## Data Upload

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

### Environment Variables and Secrets

The pipeline requires environment variables configured as **GitHub Secrets** in each environment. Without these, the upload step will fail.

#### Required Secrets per Environment

Each GitHub Environment (PROD, INT, TEST) must have the following secrets:

| Secret | Description |
|--------|-------------|
| `ENDPOINT_USER` | Your LINDAS username |
| `ENDPOINT_PASSWORD` | The password for your LINDAS account |
| `ENDPOINT_URL` | The LINDAS SPARQL endpoint URL |
| `ENDPOINT_GRAPH` | The named graph URI for your dataset |

#### Setting up GitHub Environments

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Environments**
3. Create three environments: `PROD`, `INT`, and `TEST`
4. For each environment, add the secrets listed above with the appropriate values
5. Optionally, add protection rules to the `PROD` environment (e.g., required reviewers)

#### Workflow Environment Variables

The workflow also uses these variables (configured in `pipeline.yml`):

| Variable | Description | Default |
|----------|-------------|---------|
| `UPLOAD_METHOD` | HTTP method for upload (`PUT` or `POST`) | `POST` |
| `UPLOAD_PATH` | Directory containing `.ttl` files | `outputs` |

### Upload methods

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

## Project Structure

```
├── .github/workflows/pipeline.yml  # CI/CD workflow
├── inputs/
│   ├── metadata.yml                # Cube metadata description
│   └── full_metadata.yml           # Extended metadata template
├── outputs/
│   └── cube.ttl                    # Generated RDF output
├── main.py                         # Pipeline orchestration
├── upload.sh                       # LINDAS upload script
├── requirements.txt                # Python dependencies
└── README.md
```
