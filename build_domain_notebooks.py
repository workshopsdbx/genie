"""Generate the four per-domain workshop notebooks from genie_byoq_nyc_workshop.py (the all-in-one source).

Each attendee runs only the notebook for their domain, so it finishes in a few minutes. Every domain's generator
has its own random seed, so the data is identical to the all-in-one build.
Run: python3 build_domain_notebooks.py
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).parent
src = (ROOT / "genie_byoq_nyc_workshop.py").read_text()

# (key, output file, title, schema, section heading marker in the source)
DOMAINS = [
    ("aging", "genie_nyc_aging.py", "NYC Aging & Home Care", "nyc_aging_home_care", "## 1 · NYC Aging & Home Care"),
    ("transit", "genie_nyc_transit.py", "NYC Transit Finance", "nyc_transit_finance", "## 2 · Transit Finance"),
    ("water", "genie_nyc_water.py", "NYC DEP Water & Sewer", "nyc_dep_water", "## 3 · NYC DEP Water & Sewer"),
    ("health", "genie_nyc_dohmh.py", "NYC DOHMH Food Safety & Rodents", "nyc_dohmh_food_safety", "## 4 · NYC DOHMH Food Safety"),
]
END_MARKER = "# MAGIC %md ## 5 · Grant attendee access"


def md_start(marker):
    """Index of the '# MAGIC %md' line that opens the markdown cell containing marker."""
    return src.rindex("# MAGIC %md", 0, src.index(marker))


starts = [md_start(m) for *_, m in DOMAINS] + [src.index(END_MARKER)]
sections = {d[0]: src[starts[i]:starts[i + 1]] for i, d in enumerate(DOMAINS)}
first_cell_end = src.index("# COMMAND ----------")  # the title/markdown cell
body = src[first_cell_end:starts[0]] + "{SECTION}" + src[starts[-1]:]

for key, fname, title, schema, _ in DOMAINS:
    header = f'''# Databricks notebook source
# MAGIC %md
# MAGIC # Genie Workshop — {title}
# MAGIC
# MAGIC Builds the **{title}** workshop data in schema `{schema}`: synthetic tables (with Unity Catalog descriptions
# MAGIC Genie can read), the domain's **metric view**, and a ready-made **"{title} (Starter)"** Genie space as a fallback.
# MAGIC All data is synthetic.
# MAGIC
# MAGIC **How to run:** connect to **Serverless** (top right), then click **Run all**. Leave the widgets blank: the notebook
# MAGIC finds your catalog (usually `workspace`) and SQL warehouse on its own. Takes a few minutes.
# MAGIC
# MAGIC Stuck later, or want the finished version? Run **`genie_byoq_nyc_curated_spaces`** to create the Curated answer-key space.

'''
    out = header + body.replace("{SECTION}", sections[key])
    out = out.replace('BUILD = ["aging", "transit", "water", "health"]', f'BUILD = ["{key}"]', 1)
    # Summary cell: only this domain's schema
    out = re.sub(r"# MAGIC ```\n(# MAGIC .*\n)*?# MAGIC ```\n", f"# MAGIC Schema built: `{schema}` (see the table list below).\n", out, count=1)
    # Renumber section headings 1, 2, 3, ...
    n = iter(range(1, 100))
    out = re.sub(r"(# MAGIC (?:%md )?## )\d+( · )", lambda m: f"{m.group(1)}{next(n)}{m.group(2)}", out)
    (ROOT / fname).write_text(out)
    print(f"wrote {fname} ({len(out):,} bytes)")
