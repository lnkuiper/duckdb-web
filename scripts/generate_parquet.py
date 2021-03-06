import os, sys, subprocess, re, time, threading, sqlite3, sys
import duckdb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import duckdb_query_graph
import json
import re

duckdb_web_base = os.getcwd()
benchmark_dir = os.path.join('..', 'benchmark-results')
# image_dir = os.path.join('images', 'graphs')
image_dir = os.path.join('..', 'benchmark-results', 'graphs')
groups_dir = os.path.join(benchmark_dir, 'groups')
individual_benchmarks_dir = os.path.join(benchmark_dir, 'benchmarks')
sqlite_db_file = os.path.join(duckdb_web_base, 'benchmarks.db')
# sqlite_db_file = os.path.join(duckdb_web_base, 'minibenchmarks.db')

con = sqlite3.connect(sqlite_db_file)
c = con.cursor()

# generate the group parquet files
c.execute("select distinct groupname from benchmarks where groupname is not null and groupname <> ''")
groups = [x[0] for x in c.fetchall()]

if not os.path.isdir(benchmark_dir):
	os.mkdir(benchmark_dir)

if not os.path.isdir(groups_dir):
	os.mkdir(groups_dir)

if not os.path.isdir(individual_benchmarks_dir):
	os.mkdir(individual_benchmarks_dir)

for groupname in groups:
	if '[' in groupname or '.' in groupname or '/' in groupname:
		print("WARNING: Skipping " + groupname + " for parquet file generation because it contains special characters")
		continue
	# get the 15 most recent commits that ran this benchmark
	c.execute('''
SELECT DISTINCT commits.hash, commits.date
FROM commits, benchmarks, timings
WHERE timings.benchmark_id=benchmarks.id
  AND commits.hash=timings.hash
  AND groupname = '%s'
ORDER BY commits.date DESC
LIMIT 15
''' % (groupname,))
	commits = ["'" + x[0] + "'" for x in c.fetchall()]

	query = '''
SELECT timings.hash, commits.date, benchmarks.name, benchmarks.subgroup, timings.median, timings.success, benchmarks.id
FROM timings, benchmarks, commits
WHERE benchmark_id=benchmarks.id
  AND commits.hash=timings.hash
  AND groupname = '%s'
  AND timings.hash IN (%s)
ORDER BY benchmarks.name ASC, date DESC
''' % (groupname, ', '.join(commits))
	c.execute(query)
	qresults      = c.fetchall()
	hashes        = [x[0] for x in qresults]
	dates         = [x[1] for x in qresults]
	benchmarks    = [x[2] for x in qresults]
	subgroups     = [x[3] for x in qresults]
	timings       = [x[4] for x in qresults]
	successes     = [x[5] for x in qresults]
	benchmark_ids = [x[6] for x in qresults]
	df = pd.DataFrame({
					'hash': hashes,
					'date': dates,
					'benchmark_name': benchmarks,
					'subgroups': subgroups,
					'benchmark_id': benchmark_ids,
					'timing': timings,
					'success': successes
					})

	fname = os.path.join(groups_dir, groupname + ".parquet")
	table = pa.Table.from_pandas(df)
	pq.write_table(table, fname)

# generate the benchmarks file with benchmark metadata
c.execute("select id, name, groupname, subgroup, description from benchmarks;")
qresults = c.fetchall()
ids = [x[0] for x in qresults]
names = [x[1] for x in qresults]
groups = [x[2] for x in qresults]
subgroups = [x[3] for x in qresults]
descriptions = [x[4] for x in qresults]
images = []
# load the graphs from disk
for i in range(len(ids)):
	graph_name = str(ids[i])
	# graph_name = names[i]
	graph_path = os.path.join(image_dir, graph_name + ".png")
	if os.path.exists(graph_path):
		with open(graph_path, 'rb') as f:
			images.append(f.read())
	else:
		images.append(None)

df = pd.DataFrame({
				'id': ids,
				'name': names,
				'group': groups,
				'subgroup': subgroups,
				'description': descriptions,
				'images': images})

fname = os.path.join(benchmark_dir, "benchmarks.parquet")
table = pa.Table.from_pandas(df)
pq.write_table(table, fname)

# generate the group data
c.execute("select name, subgroup, display_name, description from groups;")
qresults = c.fetchall()
names = [x[0] for x in qresults]
subgroups = [x[1] for x in qresults]
display_names = [x[2] for x in qresults]
descriptions = [x[3] for x in qresults]

df = pd.DataFrame({
				'name': names,
				'subgroup': subgroups,
				'display_name': display_names,
				'description': descriptions})

fname = os.path.join(benchmark_dir, "groups.parquet")
table = pa.Table.from_pandas(df)
pq.write_table(table, fname)

# now for each benchmark generate the benchmark name
for benchmark_id in ids:
	c.execute('''
SELECT commits.hash, commits.date, commits.message, timings.median, timings.error, timings.profile, timings.stdout, timings.stderr
FROM commits, timings
WHERE commits.hash=timings.hash
AND benchmark_id=%d
ORDER BY date DESC
''' % (benchmark_id,))
	qresults = c.fetchall()
	hashes      = [x[0] for x in qresults]
	dates       = [x[1] for x in qresults]
	messages    = [x[2] for x in qresults]
	timings     = [x[3] for x in qresults]
	errors      = [x[4] for x in qresults]
	profiles    = [x[5] for x in qresults]
	stdouts     = [x[6] for x in qresults]
	stderrs     = [x[7] for x in qresults]

	df = pd.DataFrame({
					'hash': hashes,
					'date': dates,
					'message': messages,
					'timing': timings,
					'profile': profiles,
					'error': errors,
					'stdout': stdouts,
					'stderr': stderrs})

	fname = os.path.join(individual_benchmarks_dir, str(benchmark_id) + ".parquet")
	table = pa.Table.from_pandas(df)
	pq.write_table(table, fname)
