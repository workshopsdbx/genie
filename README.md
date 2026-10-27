# Genie BYOQ Workshop: NYC Public Sector

**Workshop site:** https://workshopsdbx.github.io/genie/

The NYC rebuild of the Harrisburg PA workshop: a setup notebook plus a self-guided HTML instruction site.
Attendees each use their own **Databricks Free Edition** workspace: import the notebook, Run all, then follow the site.

| Path | What it is |
|---|---|
| `genie_byoq_nyc_workshop.py` | Databricks notebook (SOURCE format). Builds 4 schemas / 29 synthetic tables + 4 metric views, creates or updates Starter + Curated Genie spaces per domain, optional grants, and self-tests the answer key. |
| `genie_byoq_nyc_curated_spaces.py` | Notebook 2 (optional). Creates the four Curated answer-key Genie spaces for attendees who get stuck or want to skip ahead. **Generated** from notebook 1 by `build_curated_notebook.py`: re-run that after editing the answer key. |
| `site/` | Static workshop site (`index.html` + `styles.css` + `app.js`). Open `index.html` directly or host it anywhere. |
| `site/config.js` | Default catalog shown in the guide (`workspace`). Attendees can override it on the page. |
| `site/content.js` | Generated. Lab 4 answer key + Lab 3 expected answers. |
| `build_site_content.py` | Regenerates `content.js` from the notebook's `DOMAINS` answer key (`python3 build_site_content.py answers.json`). |
| `compute_answers.py` | Queries the built tables for Lab 3 expected answers (`python3 compute_answers.py <profile> <warehouse_id> <catalog>`). |

Each domain also gets a UC metric view (`client_metrics`, `transit_operating_metrics`, `water_billing_metrics`, `inspection_metrics`) and a parameterized trusted query.

Domains: `nyc_aging_home_care` (NYC Aging / HRA / MLTC), `nyc_transit_finance` (MTA + ferries + congestion pricing),
`nyc_dep_water` (DEP / Water Board), `nyc_dohmh_food_safety` (DOHMH restaurant inspections + rodent control). All data is synthetic.

Notebook widgets: `catalog` and `warehouse_id` (blank = auto-detect), `genie_spaces` (curated default / both / starter / none), `share_with_group` (paid workspaces),
`metadata_level` (basic = Lab 3 traps fire; rich = UC comments include usage rules, for the "metadata alone" demo).

If you change the notebook answer key: re-run the notebook, then `compute_answers.py`, then `build_site_content.py`, and copy the notebook into `site/`.
