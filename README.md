# LLM4VKG Matcher Improvement

This project explores improvements to matching relational database schemas with ontology concepts using LLM4VKG.

We investigate value examples and column profiles for database-to-ontology matching.
Planned experiments include Jev vs LLMs, adapting methods from the literature, and
starting from an empty ontology. EDA prepares the data; it does not measure model quality yet.

## Data acquisition

The current analysis uses four datasets in `datasets/` (the earlier CMT-only version used `dataset/`).
The files are available locally; no separate download is needed when these folders are present in your checkout.
If a dataset is missing, obtain it from the source below and preserve the listed directory structure.

| Dataset | Contents | Source | Local path |
| --- | --- | --- | --- |
| CMT structured | Papers, authors, reviews, and program committees | [LLM4VKG scenario](https://github.com/HomuraT/LLM4VKG/tree/main/datasets/rodi/cmt_structured) | `datasets/rodi/cmt_structured/` |
| SIGKDD renamed | Conference organization, papers, participants, sponsors, and registration | [LLM4VKG scenario](https://github.com/HomuraT/LLM4VKG/tree/main/datasets/rodi/sigkdd_renamed) | `datasets/rodi/sigkdd_renamed/` |
| Chinook | Music catalog, customers, and sales | [PostgreSQL dump](https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_PostgreSql.sql) | `datasets/chinook/Chinook_PostgreSql.sql` |
| Northwind | Products, suppliers, customers, and orders | [PostgreSQL dump](https://raw.githubusercontent.com/pthom/northwind_psql/master/northwind.sql) | `datasets/northwind/northwind.sql` |

For each RODI scenario, retain the complete folder, including:

| File | Description |
| --- | --- |
| `dump.sql` | PostgreSQL dump of the scenario. |
| `ontology.ttl` | Ontology in RDF/Turtle, used for analysis. |
| `ontology.owl` | Ontology in OWL/XML, preserved as a source. |
| `queries/*.qpair` | Reference SQL-SPARQL query pairs. |

The earlier CMT-only README identified its three source files with the
[LLM4VKG `cmt_structured` scenario at commit f107bd9](https://github.com/HomuraT/LLM4VKG/tree/f107bd9b737aa37c69ad55c4b9f3435137122b32/datasets/rodi/cmt_structured).
For the current collection, the [SHA-256 manifest](docs/results/files.csv) identifies local file versions;
the download commit was not recorded. Additional scenarios are available in the
[LLM4VKG datasets](https://github.com/HomuraT/LLM4VKG/tree/main/datasets/rodi).

## Exploratory data analysis (EDA)

- [Notebook](docs/EDA.ipynb): code, results, and findings in English.
- [HTML report](docs/EDA.html): results without code.
- [Full profiles and import logs](docs/results/): detailed statistics and checks.

The notebook imports the dumps into PostgreSQL and checks record counts across
source dumps, SQL tables, and DataFrames. It covers:

- schema completeness, missing values, empty tables, and primary/foreign key integrity;
- ontology classes and properties, graph sizes, relation types, and textual descriptions;
- reference query availability and SQL execution;
- implications for preprocessing and matcher design, resource estimates, and conclusions.

**Findings for CMT:** 32 tables, 5,386 rows, 20 empty tables, and 19.46% NULL values.
The current EDA also covers SIGKDD, Chinook, and Northwind; see the notebook for the complete comparison.
EDA runs on a CPU without GPU or LLM API calls. Missing values and empty tables need interpretation before preprocessing.

The ontology graph statistics do not describe a materialized VKG. Reproducing the
paper's evaluation additionally requires scenario configuration and mappings, and
executing SPARQL through a VKG to compare its answers with the reference SQL results.
Chinook and Northwind have no reference ontology or SQL-SPARQL pairs in this project.

### Setup (Linux / WSL)

Use Python 3.12 and PostgreSQL server/client tools. No Docker is required.
On Debian/Ubuntu, install the prerequisites:

```bash
sudo apt update
sudo apt install python3 python3-venv postgresql postgresql-client libpq-dev
```

Check that `python3 --version` reports the intended Python version. From the project
root, run setup as a regular user (without `sudo`):

```bash
bash scripts/setup_eda.sh
```

Setup installs [requirements-eda.txt](requirements-eda.txt) into `.eda_runtime/venv`,
creates a separate PostgreSQL cluster, and starts it on `127.0.0.1:55439`, with user
`eda` and no password (local testing only). PostgreSQL binaries are located using
`pg_config` or `pg_ctl`; set `PG_BINDIR` if they are installed elsewhere:

```bash
PG_BINDIR=/usr/lib/postgresql/16/bin bash scripts/setup_eda.sh
```

Adjust that example to your installed PostgreSQL version. Use a fresh `.eda_runtime`
on Linux/WSL; Windows virtual environments and database clusters cannot be reused there.
The setup script targets Linux/WSL, not native PowerShell.

### Run the notebook

After setup, execute all cells and save their outputs from the project root:

```bash
./.eda_runtime/venv/bin/python -m jupyter nbconvert \
  --to notebook --execute --inplace \
  --ExecutePreprocessor.timeout=600 docs/EDA.ipynb
```

Refresh the HTML report after a successful run:

```bash
./.eda_runtime/venv/bin/python -m jupyter nbconvert \
  --to html --no-input docs/EDA.ipynb
```

Alternatively, open `docs/EDA.ipynb` in VS Code, select
`.eda_runtime/venv/bin/python` as the notebook kernel, and choose **Run All**.
The notebook can run from the project root or `docs/`; PostgreSQL must be running first.
Rerun `bash scripts/setup_eda.sh` to start the existing cluster if it has been stopped.

The analysis creates temporary databases and removes them after use. Raw files remain
unchanged. Import copies omit only the obsolete `default_with_oids` setting and
Chinook database creation/switching commands. Import stops on any SQL error.
Profiles and import logs are written to `docs/results/`.

Stop the local PostgreSQL cluster after use:

```bash
"$(cat .eda_runtime/pg_bin.txt)/pg_ctl" -D .eda_runtime/pgdata -m fast stop
```

## License and attribution

- Project code and documentation: [MIT](LICENSE).
- CMT dataset (`cmt_structured`): [MIT, as distributed by RODI](https://github.com/chrpin/rodi/blob/64ae74ba2b9d21e98733e0ddfbd3a1ffae73706a/LICENSE). Copyright (c) 2015 Christoph Pinkel, fluid Operations AG. Redistribution requires preserving the original copyright and license notice.
- For other RODI material, consult the [RODI repository](https://github.com/chrpin/rodi) and the distributed notices.
- Chinook: [upstream license](https://github.com/lerocha/chinook-database/blob/master/LICENSE.md).
- Northwind PostgreSQL port: [upstream repository and attribution](https://github.com/pthom/northwind_psql).

The project's code license should not be assumed to cover external datasets.

## References

- Xiao et al. (2025). [*LLM4VKG: Leveraging Large Language Models for Virtual Knowledge Graph Construction*](https://doi.org/10.24963/ijcai.2025/525). [Authors' implementation](https://github.com/HomuraT/LLM4VKG).
- [RODI: Relational-to-Ontology Mapping Quality Benchmark](https://github.com/chrpin/rodi). Pinkel et al. (2018), [paper](https://doi.org/10.3233/SW-170268).
- Nguyen et al. (2025), [KROMA](https://arxiv.org/abs/2507.14032).
- Parciak et al. (2024), [Schema Matching with Large Language Models](https://www.vldb.org/workshops/2024/proceedings/TaDA/TaDA.8.pdf).
- [Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev): a vendor description, not a published RODI experiment.
