"""Generate genie_byoq_nyc_curated_spaces.py (notebook 2) from the answer key in genie_byoq_nyc_workshop.py.

Notebook 2 only creates/updates the Curated answer-key Genie spaces, so attendees can skip ahead or get unstuck.
Run: python3 build_curated_notebook.py
"""
import pathlib

ROOT = pathlib.Path(__file__).parent
src = (ROOT / "genie_byoq_nyc_workshop.py").read_text()
SEP = "# COMMAND ----------"


def cell_from(marker):
    start = src.index(marker)
    end = src.index(SEP, start)
    return src[start:end].rstrip() + "\n"


answer_key = cell_from('A = f"{CATALOG}.{SCHEMA_AGING}"')
helpers = cell_from("import json\nimport uuid")
upsert = cell_from("SPACE_IDS = {}")

out = f'''# Databricks notebook source
# MAGIC %md
# MAGIC # Genie BYOQ Workshop — Notebook 2: Curated answer-key spaces
# MAGIC
# MAGIC **Run this only if you're stuck or want to skip ahead.** It creates four finished **"… (Curated)"** Genie spaces,
# MAGIC one per domain, with everything from Lab 4: text instructions, example SQL, joins, SQL measures, the metric view,
# MAGIC and a benchmark set. Open yours from the Genie list and compare it with the space you built.
# MAGIC
# MAGIC **Run `genie_byoq_nyc_workshop` (notebook 1) first.** This notebook only adds Genie spaces: it doesn't create data.
# MAGIC
# MAGIC **How to run:** connect to **Serverless**, then **Run all** (about a minute). Leave the widgets blank.
# MAGIC Re-running is safe: spaces are updated in place, and the space you built yourself isn't touched.

{SEP}

dbutils.widgets.text("catalog", "", "Unity Catalog (blank = auto)")
dbutils.widgets.text("warehouse_id", "", "SQL Warehouse ID (blank = auto)")

CATALOG = dbutils.widgets.get("catalog").strip()
if not CATALOG:
    CATALOG = spark.sql("SELECT current_catalog()").first()[0]
    if CATALOG in (None, "", "hive_metastore", "spark_catalog", "system", "samples"):
        CATALOG = "workspace"
WAREHOUSE_ID = dbutils.widgets.get("warehouse_id").strip()
GENIE_MODE = "curated"
SHARE_GROUP = ""

SCHEMA_AGING = "nyc_aging_home_care"
SCHEMA_TRANSIT = "nyc_transit_finance"
SCHEMA_WATER = "nyc_dep_water"
SCHEMA_HEALTH = "nyc_dohmh_food_safety"
print(f"Catalog : {{CATALOG}}")

{SEP}

# MAGIC %md ### Check that notebook 1 has run

{SEP}

NEEDED = [f"{{CATALOG}}.{{s}}.{{t}}" for s, t in [
    (SCHEMA_AGING, "client_metrics"), (SCHEMA_TRANSIT, "transit_operating_metrics"),
    (SCHEMA_WATER, "water_billing_metrics"), (SCHEMA_HEALTH, "inspection_metrics")]]
missing = [t for t in NEEDED if not spark.catalog.tableExists(t)]
if missing:
    raise RuntimeError("Run the genie_byoq_nyc_workshop notebook first. Missing: " + ", ".join(missing))
print("Workshop data and metric views found.")

{SEP}

# MAGIC %md ### Answer key (generated from notebook 1, so the two always match)

{SEP}

{answer_key}
{SEP}

{helpers}
{SEP}

# MAGIC %md ### Create or update the Curated spaces

{SEP}

{upsert}
'''
(ROOT / "genie_byoq_nyc_curated_spaces.py").write_text(out)
print(f"wrote genie_byoq_nyc_curated_spaces.py ({len(out):,} bytes)")
