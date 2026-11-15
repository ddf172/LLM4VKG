
# Setups and starts local Postgres server to use in EDA

#!/usr/bin/env bash
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$root"
runtime="$root/.eda_runtime"

if (( EUID == 0 )); then
    echo 'Run this script as a regular user; PostgreSQL cannot run as root.' >&2
    exit 1
fi

# Debian/Ubuntu keep server binaries outside PATH; pg_config locates them.
pg_bin="${PG_BINDIR:-}"
if [[ -z "$pg_bin" ]] && command -v pg_config >/dev/null 2>&1; then
    pg_bin="$(pg_config --bindir)"
fi
if [[ -z "$pg_bin" ]] && command -v pg_ctl >/dev/null 2>&1; then
    pg_bin="$(dirname -- "$(command -v pg_ctl)")"
fi
for tool in initdb pg_ctl psql; do
    if [[ ! -x "$pg_bin/$tool" ]]; then
        echo 'Install PostgreSQL server/client tools or set PG_BINDIR to their bin directory.' >&2
        echo 'Debian/Ubuntu: sudo apt install python3 python3-venv postgresql postgresql-client libpq-dev' >&2
        exit 1
    fi
done

mkdir -p "$runtime"
python3 -m venv "$runtime/venv"
"$runtime/venv/bin/python" -m pip install -r "$root/requirements-eda.txt"
printf '%s\n' "$pg_bin" > "$runtime/pg_bin.txt"

if [[ ! -f "$runtime/pgdata/PG_VERSION" ]]; then
    "$pg_bin/initdb" -D "$runtime/pgdata" -U eda -A trust -E UTF8 --locale=C
fi
if ! "$pg_bin/pg_ctl" -D "$runtime/pgdata" status >/dev/null 2>&1; then
    "$pg_bin/pg_ctl" -D "$runtime/pgdata" -l "$runtime/postgres.log" \
        -o "-p 55439 -h 127.0.0.1 -k /tmp" -w start
fi
echo 'Ready. Run: ./.eda_runtime/venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=600 docs/EDA.ipynb'
