# LLM4VKG — custom matcher

We investigate value examples and column profiles for database-to-ontology matching.
Planned experiments: Jev vs LLMs, adapting methods from the literature, and starting
from an empty ontology. EDA prepares the data; it does not measure model quality yet.

## Data

| Dataset | Source / download | Local path |
|---|---|---|
| CMT structured, SIGKDD renamed | [LLM4VKG](https://github.com/HomuraT/LLM4VKG/tree/main/datasets/rodi): Code → Download ZIP, copy both complete folders | `datasets/rodi/` |
| Chinook 1.4.5 | Save the [PostgreSQL SQL file](https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_PostgreSql.sql) | `datasets/chinook/Chinook_PostgreSql.sql` |
| Northwind | Save the [PostgreSQL SQL file](https://raw.githubusercontent.com/pthom/northwind_psql/master/northwind.sql) | `datasets/northwind/northwind.sql` |

For RODI, keep the dump, ontologies, and `queries/*.qpair`. The
[SHA-256 manifest](docs/results/files.csv) identifies local file versions;
the download commit was not recorded.
Sources and usage terms: [RODI](https://github.com/chrpin/rodi),
[Chinook](https://github.com/lerocha/chinook-database/blob/master/LICENSE.md),
[Northwind port](https://github.com/pthom/northwind_psql).
The project's code license should not be assumed to cover external datasets.

## EDA

- [Notebook](docs/EDA.ipynb) — code, results, and findings in English.
- [HTML report](docs/EDA.html) — the same results without code.
- [Full profiles and logs](docs/results/) — details outside the main narrative.

Linux, Python 3.12, no Docker required. Install prerequisites first (Debian/Ubuntu):

```bash
sudo apt install python3 python3-venv postgresql postgresql-client libpq-dev
```

Then run from the project directory as a regular user (without sudo):

```bash
bash scripts/setup_eda.sh
./.eda_runtime/venv/bin/python scripts/run_eda.py
```

Setup installs Python dependencies into `.eda_runtime/venv` and uses the installed
PostgreSQL binaries, located via `pg_config` or `pg_ctl` on PATH. Set `PG_BINDIR`
explicitly if needed. Use a fresh `.eda_runtime` on Linux; do not reuse a Windows
virtual environment or database cluster.
A separate cluster runs on `127.0.0.1:55439`, with user `eda` and no password
(local testing only). The notebook creates temporary databases and removes them
after analysis. Raw files remain unchanged. Import copies omit only the obsolete
`default_with_oids` setting and Chinook database creation/switching commands.
Import stops on any error.

In VS Code, select `.eda_runtime/venv/bin/python` as the interpreter.
Stop the cluster after use:

```bash
"$(cat .eda_runtime/pg_bin.txt)/pg_ctl" -D .eda_runtime/pgdata -m fast stop
```

The original root-level `EDA.ipynb` is retained as an archive;
the current analysis is in `docs/`.

## References

- Xiao et al. (2025), [LLM4VKG](https://www.ijcai.org/proceedings/2025/0525.pdf).
- Pinkel et al. (2018), [RODI](https://doi.org/10.3233/SW-170268).
- Nguyen et al. (2025), [KROMA](https://arxiv.org/abs/2507.14032).
- Parciak et al. (2024), [Schema Matching with Large Language Models](https://www.vldb.org/workshops/2024/proceedings/TaDA/TaDA.8.pdf).
- [Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev) — a vendor description, not a published RODI experiment.
