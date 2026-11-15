"""Import and profile four local datasets in PostgreSQL. No LLM calls."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import re
import subprocess
import uuid

import pandas as pd
import psycopg
from psycopg import sql
from rdflib import Graph, RDF, RDFS, OWL, URIRef, Literal
import sqlparse
from sqlparse import tokens as T

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'results'
SOURCES = {
    'cmt_structured': 'rodi/cmt_structured/dump.sql',
    'sigkdd_renamed': 'rodi/sigkdd_renamed/dump.sql',
    'chinook': 'chinook/Chinook_PostgreSql.sql',
    'northwind': 'northwind/northwind.sql',
}
CONNECTION = dict(host='127.0.0.1', port=55439, user='eda')


def source_counts(text):
    """Independent record counts: COPY rows and VALUES tuples, without decoding data."""
    counts = Counter()
    pattern = r'^COPY (\S+) \([^\n]+\) FROM stdin;\n(.*?)^\\\.\s*$'
    for table, body in re.findall(pattern, text, re.M | re.S):
        counts[table.strip('"')] += len(body.splitlines())
    for statement in sqlparse.split(re.sub(pattern, '', text, flags=re.M | re.S)):
        match = re.search(r'\bINSERT INTO\s+("[^"]+"|\w+)', statement, re.I)
        if not match:
            continue
        depth, in_values = 0, False
        for kind, value in sqlparse.lexer.tokenize(statement):
            if kind in T.Keyword and value.upper() == 'VALUES':
                in_values = True
            elif in_values and kind == T.Punctuation:
                if value == '(':
                    counts[match[1].strip('"')] += depth == 0
                    depth += 1
                elif value == ')':
                    depth -= 1
        assert in_values and depth == 0, 'Unsupported INSERT format in source validation'
    return counts


def import_database(name, database, admin):
    raw = (ROOT / 'datasets' / SOURCES[name]).read_text(encoding='utf-8-sig')
    expected = source_counts(raw)
    # Version compatibility and database selection only: tables and values stay unchanged.
    cleaned, old_setting = re.subn(r'^SET default_with_oids = false;\s*$', '', raw, flags=re.M)
    cleaned, db_commands = re.subn(
        r'^(?:DROP DATABASE IF EXISTS chinook;|CREATE DATABASE chinook;|\\c chinook;)\s*$',
        '', cleaned, flags=re.M)
    path = ROOT / '.eda_runtime' / f'{name}.sql'
    path.write_text(cleaned, encoding='utf-8')
    admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
    pg_bin_file = ROOT / '.eda_runtime' / 'pg_bin.txt'
    psql = (Path(pg_bin_file.read_text(encoding='utf-8').strip()) / 'psql'
            if pg_bin_file.exists() else ROOT / '.eda_runtime' / 'pgsql' / 'bin' / 'psql.exe')
    result = subprocess.run(
        [str(psql), '-X', '-h', CONNECTION['host'], '-p', str(CONNECTION['port']),
         '-U', CONNECTION['user'], '-d', database, '-v', 'ON_ERROR_STOP=1',
         '--single-transaction', '-f', str(path)], capture_output=True)
    (OUT / f'{name}_import.txt').write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f'Import {name}: see docs/results/{name}_import.txt')
    return expected, {'dataset': name, 'removed_legacy_setting': old_setting,
                      'removed_database_commands': db_commands, 'exit_code': result.returncode}


def constraints(connection, namespace):
    return connection.execute('''
        SELECT t.relname, c.contype,
               ARRAY(SELECT a.attname FROM unnest(c.conkey) WITH ORDINALITY k(n,i)
                     JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.n ORDER BY k.i),
               target.relname,
               ARRAY(SELECT a.attname FROM unnest(c.confkey) WITH ORDINALITY k(n,i)
                     JOIN pg_attribute a ON a.attrelid=c.confrelid AND a.attnum=k.n ORDER BY k.i),
               c.conname
        FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid
        JOIN pg_namespace n ON n.oid=t.relnamespace
        LEFT JOIN pg_class target ON target.oid=c.confrelid
        WHERE n.nspname=%s AND c.contype IN ('p','f','u') ORDER BY t.relname,c.conname
    ''', (namespace,)).fetchall()


def profile(connection, name, expected):
    namespace = name if name in ('cmt_structured', 'sigkdd_renamed') else 'public'
    columns = connection.execute('''SELECT table_name,column_name,data_type,is_nullable
        FROM information_schema.columns WHERE table_schema=%s
        ORDER BY table_name,ordinal_position''', (namespace,)).fetchall()
    cons = constraints(connection, namespace)
    frames, tables, fields, relations = {}, [], [], []
    for table in dict.fromkeys(c[0] for c in columns):
        cursor = connection.execute(sql.SQL('SELECT * FROM {}.{}').format(
            sql.Identifier(namespace), sql.Identifier(table)))
        frame = pd.DataFrame(cursor.fetchall(), columns=[c.name for c in cursor.description], dtype=object)
        frames[table] = frame
        primary = next((c[2] for c in cons if c[0] == table and c[1] == 'p'), [])
        sql_count = connection.execute(sql.SQL('SELECT COUNT(*) FROM {}.{}').format(
            sql.Identifier(namespace), sql.Identifier(table))).fetchone()[0]
        assert sql_count == len(frame) == expected.get(table, 0), (name, table, sql_count, expected)
        tables.append(dict(dataset=name, table=table, rows=len(frame), source_rows=expected.get(table, 0),
                           columns=len(frame.columns), pk=', '.join(primary),
                           fks=sum(c[0] == table and c[1] == 'f' for c in cons),
                           duplicate_pk=int(frame.duplicated(primary).sum()) if primary else None,
                           null_pk=int(frame[primary].isna().any(axis=1).sum()) if primary else None))
        for _, col, dtype, nullable in (c for c in columns if c[0] == table):
            series = frame[col]
            valid = series.dropna()
            strings = valid.map(str)
            examples = sorted(strings.unique())[:3]
            counts = strings.value_counts()
            fields.append(dict(dataset=name, table=table, column=col, type=dtype,
                rows=len(series), nulls=int(series.isna().sum()),
                null_pct=100*series.isna().mean() if len(series) else None,
                empty=int(strings.eq('').sum()), whitespace=int((strings.ne('') & strings.str.strip().eq('')).sum()),
                distinct=int(valid.nunique()), unique_ratio=valid.nunique()/len(valid) if len(valid) else None,
                not_null_violations=int(series.isna().sum()) if nullable == 'NO' else 0,
                min_value=str(valid.min()) if len(valid) and dtype not in ('bytea',) else '',
                max_value=str(valid.max()) if len(valid) and dtype not in ('bytea',) else '',
                max_length=int(strings.str.len().max()) if len(strings) else 0,
                examples=json.dumps([v[:100] for v in examples], ensure_ascii=False),
                top_values=json.dumps({str(k)[:100]: int(v) for k,v in counts.head(3).items()}, ensure_ascii=False)))
    assert set(expected) <= set(frames), (name, 'source table missing from import')
    for table, kind, cols, target, target_cols, constraint in cons:
        if kind != 'f':
            continue
        source = frames[table][cols].dropna()  # MATCH SIMPLE: also skip partially NULL references.
        targets = set(frames[target][target_cols].itertuples(index=False, name=None))
        keys = list(source.itertuples(index=False, name=None))
        frequencies = Counter(keys)
        relations.append(dict(dataset=name, table=table, columns=', '.join(cols), target=target,
            target_columns=', '.join(target_cols), constraint=constraint, non_null=len(keys),
            orphans=sum(k not in targets for k in keys),
            distinct_targets=len(frequencies), max_incoming=max(frequencies.values(), default=0),
            self_reference=table == target))
    return tables, fields, relations, frames


def ontology_profile(name):
    folder = ROOT / 'datasets' / 'rodi' / name
    graph = Graph().parse(folder / 'ontology.ttl')
    classes = {c for c in graph.subjects(RDF.type, OWL.Class) if isinstance(c, URIRef)}
    props = {kind: set(graph.subjects(RDF.type, typ)) for kind, typ in
             [('object', OWL.ObjectProperty), ('data', OWL.DatatypeProperty)]}
    terms = classes | props['object'] | props['data']
    vertices = set(graph.subjects()) | set(graph.objects())
    stats = dict(dataset=name, triples=len(graph), predicates=len(set(graph.predicates())),
                 resource_nodes=sum(not isinstance(v, Literal) for v in vertices),
                 literal_nodes=sum(isinstance(v, Literal) for v in vertices),
                 classes=len(classes), object_properties=len(props['object']), data_properties=len(props['data']),
                 named_individuals=len(set(graph.subjects(RDF.type, OWL.NamedIndividual))),
                 explicit_class_instances=len({s for s,_,o in graph.triples((None,RDF.type,None)) if o in classes}),
                 terms=len(terms), labeled=sum(bool(list(graph.objects(t,RDFS.label))) for t in terms),
                 commented=sum(bool(list(graph.objects(t,RDFS.comment))) for t in terms),
                 subclass_axioms=len(list(graph.triples((None,RDFS.subClassOf,None)))))
    properties = [dict(dataset=name, property=str(p), kind=kind,
                      domain=' | '.join(map(str,graph.objects(p,RDFS.domain))),
                      range=' | '.join(map(str,graph.objects(p,RDFS.range))))
                  for kind, ps in props.items() for p in sorted(ps, key=str)]
    predicates = [dict(dataset=name, predicate=str(p), triples=n)
                  for p,n in Counter(graph.predicates()).most_common()]
    queries = []
    for path in sorted((folder / 'queries').glob('*.qpair')):
        text = path.read_text(encoding='utf-8')
        queries.append(dict(dataset=name, query=path.stem,
            has_sql=bool(re.search(r'^sql=', text, re.M)), has_sparql=bool(re.search(r'^sparql=', text, re.M)),
            categories=next((l.split('=',1)[1] for l in text.splitlines() if l.startswith('categories=')), '')))
    return stats, properties, predicates, queries


def check_queries(connection, name):
    """Run the reference SQL side only; this is not a VKG evaluation."""
    connection.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(name)))
    rows = []
    for path in sorted((ROOT/'datasets'/'rodi'/name/'queries').glob('*.qpair')):
        text = path.read_text(encoding='utf-8')
        query = re.search(r'^sql=(.*?)(?=^\w+=|\Z)', text, re.M | re.S)[1].strip()
        query = query.replace('\\\n', '').replace(r'\n', '\n')
        with connection.transaction():
            answer = connection.execute(query).fetchall()
        rows.append(dict(dataset=name, query=path.stem, result_rows=len(answer),
                         sample=json.dumps(answer[:3], default=str), sql_ok=True))
    return rows


def analyze():
    OUT.mkdir(parents=True, exist_ok=True)
    result = {key: [] for key in ['tables','columns','foreign_keys','imports','ontologies','properties','predicates','queries','sql_answers']}
    data = {}
    with psycopg.connect(dbname='postgres', autocommit=True, **CONNECTION) as admin:
        version = admin.execute('SELECT version()').fetchone()[0]
        for name in SOURCES:
            database = 'eda_' + name + '_' + uuid.uuid4().hex[:8]
            try:
                expected, imported = import_database(name, database, admin)
                with psycopg.connect(dbname=database, **CONNECTION) as conn:
                    conn.execute('SET TRANSACTION READ ONLY')
                    tables, columns, fks, frames = profile(conn, name, expected)
                    if name in ('cmt_structured','sigkdd_renamed'):
                        result['sql_answers'].extend(check_queries(conn, name))
                for key, rows in [('tables',tables),('columns',columns),('foreign_keys',fks)]:
                    result[key].extend(rows)
                result['imports'].append(imported)
                data[name] = frames
            finally:
                admin.execute(sql.SQL('DROP DATABASE IF EXISTS {}').format(sql.Identifier(database)))
    for name in ['cmt_structured','sigkdd_renamed']:
        stats, props, preds, queries = ontology_profile(name)
        result['ontologies'].append(stats)
        for key, rows in [('properties',props),('predicates',preds),('queries',queries)]:
            result[key].extend(rows)
    result = {key: pd.DataFrame(rows) for key,rows in result.items()}
    result['files'] = pd.DataFrame([dict(file=p.relative_to(ROOT).as_posix(), bytes=p.stat().st_size,
        sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted((ROOT/'datasets').rglob('*')) if p.is_file()])
    for key, frame in result.items():
        frame.to_csv(OUT / f'{key}.csv', index=False)
    (OUT/'environment.json').write_text(json.dumps({'postgresql':version}, indent=2), encoding='utf-8')
    return result, data
