# Databricks notebook source
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

# COMMAND ----------

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
print(f"Catalog : {CATALOG}")

# COMMAND ----------

# MAGIC %md ### Check that notebook 1 has run

# COMMAND ----------

NEEDED = [f"{CATALOG}.{s}.{t}" for s, t in [
    (SCHEMA_AGING, "client_metrics"), (SCHEMA_TRANSIT, "transit_operating_metrics"),
    (SCHEMA_WATER, "water_billing_metrics"), (SCHEMA_HEALTH, "inspection_metrics")]]
missing = [t for t in NEEDED if not spark.catalog.tableExists(t)]
if missing:
    raise RuntimeError("Run the genie_byoq_nyc_workshop notebook first. Missing: " + ", ".join(missing))
print("Workshop data and metric views found.")

# COMMAND ----------

# MAGIC %md ### Answer key (generated from notebook 1, so the two always match)

# COMMAND ----------

A = f"{CATALOG}.{SCHEMA_AGING}"
T = f"{CATALOG}.{SCHEMA_TRANSIT}"
W = f"{CATALOG}.{SCHEMA_WATER}"
H = f"{CATALOG}.{SCHEMA_HEALTH}"

DOMAINS = {
    "aging": {
        "title": "NYC Aging & Home Care",
        "description": "Frail older New Yorkers: MLTC enrollment, UAS-NY functional assessments, monthly home-care services, NYC Aging program waitlists and community-district roll-ups. Synthetic workshop data.",
        "schema": SCHEMA_AGING,
        "tables": ["clients", "functional_assessments", "home_care_services", "mltc_plans",
                   "aging_programs", "cd_aging_metrics", "community_districts"],
        "starter_instructions": "This space covers older and disabled New Yorkers served by NYC Aging, HRA and Medicaid managed long-term care. All data is synthetic.",
        "curated_instructions": (
            "This space covers older and disabled New Yorkers served by NYC Aging (formerly DFTA), HRA and Medicaid managed long-term care (MLTC). All data is synthetic.\n\n"
            "Definitions:\n"
            "- 'Frail' means clients.medically_frail = TRUE unless the user mentions the frailty index.\n"
            "- 'Isolated' or 'at risk of isolation' means medically_frail = TRUE AND living_alone = TRUE.\n"
            "- ADL = Activities of Daily Living; IADL = Instrumental ADLs. Higher = more impaired.\n"
            "- 'Eligible for personal care' or 'meets the minimum needs rule' = functional_assessments.meets_min_adl_need = TRUE.\n"
            "- 'Nursing home level of care' = functional_assessments.nursing_facility_loc = TRUE.\n\n"
            "Rules:\n"
            "- A client can have several assessments. For a client's CURRENT status, use only their most recent assessment (latest assessment_date per client_id).\n"
            "- 'This month' / 'latest month' for services = MAX(service_month) in home_care_services.\n"
            "- Per-capita rates use community_districts.population; express as per 10,000 residents.\n"
            "- When asked about waitlists, use aging_programs.waitlist.\n"
            "- 'Waiting for home care' means the EISEP Home Care waitlist only. Other waitlists (meals, case management, caregiver support) are for other services; do not add them in.\n"
            "- Always show community districts with both the code and cd_name.\n"
            "- State units: cost_usd is US dollars; units_delivered depends on unit_type (hour/day/meal).\n"
            "- For client counts, frailty and isolation, prefer the client_metrics metric view (query measures with MEASURE())."
        ),
        "sample_questions": [
            "How many medically frail clients are there in each borough?",
            "Which NYC Aging program has the longest waitlist?",
            "What is the total home care cost by service category?",
            "Which MLTC plan has the best quality score?",
            "Show the top 10 community districts by frail clients living alone.",
        ],
        "example_sqls": [
            ("Which community districts have the most frail older adults living alone?",
             f"SELECT c.community_district, d.cd_name, d.borough, COUNT(*) AS frail_living_alone\n"
             f"FROM {A}.clients c JOIN {A}.community_districts d ON c.community_district = d.community_district\n"
             f"WHERE c.medically_frail AND c.living_alone AND c.enrollment_status <> 'Disenrolled'\n"
             f"GROUP BY c.community_district, d.cd_name, d.borough ORDER BY frail_living_alone DESC LIMIT 10"),
            ("What share of clients meet the minimum ADL need for personal care, based on their latest assessment?",
             f"WITH latest AS (\n  SELECT * FROM {A}.functional_assessments\n"
             f"  QUALIFY ROW_NUMBER() OVER (PARTITION BY client_id ORDER BY assessment_date DESC) = 1\n)\n"
             f"SELECT COUNT(*) AS clients_assessed, SUM(CAST(meets_min_adl_need AS INT)) AS meets_min_need,\n"
             f"  ROUND(100.0 * SUM(CAST(meets_min_adl_need AS INT)) / COUNT(*), 1) AS pct_meets_min_need\nFROM latest"),
            ("What was the total home care cost by service category in the latest month?",
             f"SELECT service_category, unit_type, SUM(units_delivered) AS units, ROUND(SUM(cost_usd), 0) AS total_cost_usd,\n"
             f"  COUNT(DISTINCT client_id) AS clients\nFROM {A}.home_care_services\n"
             f"WHERE service_month = (SELECT MAX(service_month) FROM {A}.home_care_services)\n"
             f"GROUP BY service_category, unit_type ORDER BY total_cost_usd DESC"),
            ("Frail clients per 10,000 residents by borough",
             f"WITH pop AS (SELECT borough, SUM(population) AS population FROM {A}.community_districts GROUP BY borough),\n"
             f"frail AS (SELECT borough, COUNT(*) AS frail_clients FROM {A}.clients WHERE medically_frail GROUP BY borough)\n"
             f"SELECT p.borough, f.frail_clients, p.population, ROUND(f.frail_clients * 10000.0 / p.population, 2) AS frail_per_10k\n"
             f"FROM pop p JOIN frail f ON p.borough = f.borough ORDER BY frail_per_10k DESC"),
            ("Which MLTC plan takes longest to start services?",
             f"SELECT plan_name, plan_type, avg_days_to_service_start, nyc_enrollment\nFROM {A}.mltc_plans ORDER BY avg_days_to_service_start DESC"),
        ],
        "joins": [
            ("clients", "community_districts", "`clients`.`community_district` = `community_districts`.`community_district`", "MANY_TO_ONE"),
            ("clients", "mltc_plans", "`clients`.`plan_id` = `mltc_plans`.`plan_id`", "MANY_TO_ONE"),
            ("functional_assessments", "clients", "`functional_assessments`.`client_id` = `clients`.`client_id`", "MANY_TO_ONE"),
            ("home_care_services", "clients", "`home_care_services`.`client_id` = `clients`.`client_id`", "MANY_TO_ONE"),
        ],
        "measures": [
            ("frail_clients", "Frail clients", "SUM(CAST(clients.medically_frail AS INT))", ["frail", "medically frail count"]),
            ("total_service_cost", "Total service cost (USD)", "SUM(home_care_services.cost_usd)", ["home care spend", "service cost"]),
        ],
        "benchmarks": [
            ("How many active clients are medically frail?",
             f"SELECT COUNT(*) FROM {A}.clients WHERE medically_frail AND enrollment_status = 'Active'"),
            ("Which program has the largest waitlist?",
             f"SELECT program_name, waitlist FROM {A}.aging_programs ORDER BY waitlist DESC LIMIT 1"),
            ("How many clients are enrolled in each MLTC plan?",
             f"SELECT p.plan_name, COUNT(*) AS clients FROM {A}.clients c JOIN {A}.mltc_plans p ON c.plan_id = p.plan_id GROUP BY p.plan_name ORDER BY clients DESC"),
            ("What is the average frailty index on clients' most recent assessment, by borough?",
             f"SELECT c.borough, ROUND(AVG(a.frailty_index), 3) AS avg_frailty_index FROM (SELECT * FROM {A}.functional_assessments QUALIFY ROW_NUMBER() OVER (PARTITION BY client_id ORDER BY assessment_date DESC) = 1) a JOIN {A}.clients c ON a.client_id = c.client_id GROUP BY c.borough ORDER BY avg_frailty_index DESC"),
            ("What was total Medicaid-funded home care cost in September 2026?",
             f"SELECT ROUND(SUM(cost_usd), 0) FROM {A}.home_care_services WHERE funding_source = 'Medicaid' AND service_month = DATE'2026-09-01'"),
        ],
    },
    "transit": {
        "title": "NYC Transit Finance",
        "description": "OMB-style analysis of NYC transit: agency operating finance, farebox recovery, ridership & fare evasion, congestion-pricing revenue, funding sources and the capital program. Synthetic workshop data.",
        "schema": SCHEMA_TRANSIT,
        "tables": ["transit_agencies", "monthly_financials", "ridership", "cbd_toll_program",
                   "funding_sources", "capital_projects"],
        "starter_instructions": "This space covers NYC-area public-transit finance and ridership (MTA agencies plus NYC Ferry and the Staten Island Ferry). All data is synthetic.",
        "curated_instructions": (
            "This space covers NYC-area public-transit finance (MTA agencies, NYC DOT's Staten Island Ferry and NYCEDC's NYC Ferry). All data is synthetic.\n\n"
            "Units:\n"
            "- Every column ending in _m is MILLIONS of US dollars. public_subsidy_per_trip_usd is in DOLLARS. Always state the unit.\n\n"
            "Definitions:\n"
            "- 'Ridership' = ridership.total_trips. 'Weekday ridership' = avg_weekday_trips.\n"
            "- 'Deficit' = negative operating_balance_m. 'Cost' or 'spend' = total_expense_m.\n"
            "- 'Farebox recovery' for any period or group = SUM(fare_revenue_m) / SUM(total_expense_m). Never average farebox_recovery_ratio.\n"
            "- 'Subsidy per rider' for a period = SUM(dedicated_taxes_m + state_city_subsidy_m + federal_funds_m) * 1e6 / SUM(total_trips).\n"
            "- 'The MTA' = transit_agencies.operator = 'MTA' (NYCT-SUB, NYCT-BUS, MTABC, SIR, LIRR, MNR, AAR). Never match 'MTA' against agency_id.\n"
            "- 'The subway' = agency_id 'NYCT-SUB'; 'buses' = NYCT-BUS and MTABC; 'commuter rail' = LIRR and MNR; 'ferries' = SIF and NYCF.\n"
            "- 'Congestion pricing' = cbd_toll_program. Its net revenue funds the CAPITAL program, not operating budgets.\n\n"
            "Rules:\n"
            "- 'Last 12 months' = the 12 most recent months in the data (latest month is MAX(month)).\n"
            "- The Staten Island Ferry is fare-free; exclude SIF when ranking agencies by farebox recovery unless asked. Filter on agency_id (or the metric view's `Agency ID`), not the agency name, and drop NULL ratios before ranking.\n"
            "- The MTA fiscal year equals the calendar year (use calendar_year).\n"
            "- For revenue, expense, deficit, subsidy and farebox questions, prefer the transit_operating_metrics metric view (query measures with MEASURE())."
        ),
        "sample_questions": [
            "Which agency had the largest operating deficit over the last 12 months?",
            "What is the subway's farebox recovery ratio in 2025?",
            "How much net revenue has congestion pricing raised so far?",
            "Which agency has the highest fare evasion rate?",
            "List capital projects that are over budget.",
        ],
        "example_sqls": [
            ("Operating deficit by agency over the last 12 months",
             f"SELECT f.agency_id, a.agency_name, ROUND(SUM(f.operating_balance_m), 1) AS operating_balance_m\n"
             f"FROM {T}.monthly_financials f JOIN {T}.transit_agencies a ON f.agency_id = a.agency_id\n"
             f"WHERE f.month > add_months((SELECT MAX(month) FROM {T}.monthly_financials), -12)\n"
             f"GROUP BY f.agency_id, a.agency_name ORDER BY operating_balance_m ASC"),
            ("Farebox recovery ratio by agency for 2025",
             f"SELECT a.agency_name, ROUND(SUM(f.fare_revenue_m) / SUM(f.total_expense_m), 3) AS farebox_recovery_ratio\n"
             f"FROM {T}.monthly_financials f JOIN {T}.transit_agencies a ON f.agency_id = a.agency_id\n"
             f"WHERE f.calendar_year = 2025 AND f.agency_id <> 'SIF'\n"
             f"GROUP BY a.agency_name ORDER BY farebox_recovery_ratio DESC"),
            ("Public subsidy per trip by agency in 2025",
             f"SELECT a.agency_name, ROUND(SUM(f.dedicated_taxes_m + f.state_city_subsidy_m + f.federal_funds_m) * 1e6 / SUM(r.total_trips), 2) AS subsidy_per_trip_usd\n"
             f"FROM {T}.monthly_financials f\nJOIN {T}.ridership r ON f.agency_id = r.agency_id AND f.month = r.month\n"
             f"JOIN {T}.transit_agencies a ON f.agency_id = a.agency_id\nWHERE f.calendar_year = 2025\n"
             f"GROUP BY a.agency_name ORDER BY subsidy_per_trip_usd DESC"),
            ("How much net revenue has congestion pricing generated since launch?",
             f"SELECT MIN(month) AS first_month, MAX(month) AS latest_month, ROUND(SUM(net_revenue_m), 1) AS net_revenue_m,\n"
             f"  ROUND(AVG(traffic_reduction_pct), 1) AS avg_traffic_reduction_pct\nFROM {T}.cbd_toll_program"),
            ("Subway ridership year over year by month",
             f"SELECT month, total_trips, LAG(total_trips, 12) OVER (ORDER BY month) AS trips_prior_year,\n"
             f"  ROUND(100.0 * (total_trips / LAG(total_trips, 12) OVER (ORDER BY month) - 1), 1) AS yoy_pct\n"
             f"FROM {T}.ridership WHERE agency_id = 'NYCT-SUB' ORDER BY month"),
        ],
        "joins": [
            ("monthly_financials", "transit_agencies", "`monthly_financials`.`agency_id` = `transit_agencies`.`agency_id`", "MANY_TO_ONE"),
            ("ridership", "transit_agencies", "`ridership`.`agency_id` = `transit_agencies`.`agency_id`", "MANY_TO_ONE"),
            ("monthly_financials", "ridership", "`monthly_financials`.`agency_id` = `ridership`.`agency_id` AND `monthly_financials`.`month` = `ridership`.`month`", "ONE_TO_ONE"),
            ("capital_projects", "transit_agencies", "`capital_projects`.`agency_id` = `transit_agencies`.`agency_id`", "MANY_TO_ONE"),
        ],
        "measures": [
            ("farebox_recovery", "Farebox recovery ratio", "SUM(monthly_financials.fare_revenue_m) / SUM(monthly_financials.total_expense_m)", ["farebox", "fare recovery"]),
            ("operating_balance", "Operating balance ($M)", "SUM(monthly_financials.operating_balance_m)", ["deficit", "surplus", "net operating result"]),
        ],
        "benchmarks": [
            ("What was total subway ridership in 2025?",
             f"SELECT SUM(total_trips) FROM {T}.ridership WHERE agency_id = 'NYCT-SUB' AND YEAR(month) = 2025"),
            ("What was the MTA-wide farebox recovery ratio in 2025?",
             f"SELECT ROUND(SUM(f.fare_revenue_m) / SUM(f.total_expense_m), 3) FROM {T}.monthly_financials f JOIN {T}.transit_agencies a ON f.agency_id = a.agency_id WHERE a.operator = 'MTA' AND f.calendar_year = 2025"),
            ("What share of FY2026 funding is capital versus operating?",
             f"SELECT budget_type, SUM(amount_m) AS amount_m, ROUND(100 * SUM(amount_m) / SUM(SUM(amount_m)) OVER (), 1) AS pct FROM {T}.funding_sources GROUP BY budget_type"),
            ("Which capital projects have spent more than their budget?",
             f"SELECT project_id, project_name, budget_m, spent_to_date_m FROM {T}.capital_projects WHERE spent_to_date_m > budget_m ORDER BY spent_to_date_m - budget_m DESC"),
            ("What was average daily congestion zone entries in the most recent month?",
             f"SELECT month, avg_daily_entries FROM {T}.cbd_toll_program ORDER BY month DESC LIMIT 1"),
        ],
    },
    "water": {
        "title": "NYC DEP Water & Sewer",
        "description": "NYC DEP / Water Board operations and affordability: billing and arrears, rate schedules by fiscal year, water main breaks, DEP 311 requests, reservoir storage, assistance programs and infrastructure condition. Synthetic workshop data.",
        "schema": SCHEMA_WATER,
        "tables": ["water_accounts", "monthly_billing", "rate_schedules", "water_main_breaks",
                   "service_requests_311", "reservoir_storage", "assistance_programs",
                   "infrastructure_assets", "community_districts"],
        "starter_instructions": "This space covers NYC DEP water and sewer operations, billing and affordability. All data is synthetic.",
        "curated_instructions": (
            "This space covers NYC Department of Environmental Protection (DEP) water and sewer operations, billing and affordability. All data is synthetic.\n\n"
            "Time:\n"
            "- NYC fiscal year runs July 1 - June 30. 'FY2026' = Jul 2025 - Jun 2026. Use the fiscal_year column when a user says FY.\n"
            "- 'Winter' = December, January and February. 'Last winter' = the most recent complete Dec-Feb (Dec 2025 - Feb 2026 in this data).\n\n"
            "Definitions:\n"
            "- 'Arrears' or 'debt' = monthly_billing.arrears_balance_usd. It is a running balance: ALWAYS filter to one bill_month (default the latest, MAX(bill_month)); never sum across months.\n"
            "- 'Delinquent' = arrears_balance_usd > 0 in the latest month. 'Lien-eligible' = water_accounts.account_status = 'Lien-Eligible'.\n"
            "- 1 ccf = 100 cubic feet = 748 gallons.\n"
            "- 'Trunk main' = main_diameter_in >= 20.\n"
            "- 'No water complaints' = service_requests_311.descriptor = 'No Water'. Response time = days_to_close for Closed requests.\n"
            "- System-wide reservoir level for a date = SUM(storage_bg) / SUM(capacity_bg) * 100. Never average pct_full.\n\n"
            "Rules:\n"
            "- rate_schedules has one row per rate_code per fiscal_year: join on BOTH rate_code and fiscal_year.\n"
            "- Show community districts with both code and cd_name (join community_districts).\n"
            "- Dollar columns are USD unless suffixed _m (millions).\n"
            "- For billing, arrears and delinquency questions, prefer the water_billing_metrics metric view (query measures with MEASURE())."
        ),
        "sample_questions": [
            "What is the total arrears balance by borough?",
            "How many water main breaks happened each winter?",
            "What is the average time to close No Water complaints by borough?",
            "How full are the reservoirs right now compared to normal?",
            "Which assistance program has issued the most credits?",
        ],
        "example_sqls": [
            ("Total arrears and delinquent accounts by borough as of the latest month",
             f"SELECT a.borough, COUNT_IF(b.arrears_balance_usd > 0) AS delinquent_accounts,\n"
             f"  ROUND(SUM(b.arrears_balance_usd), 0) AS total_arrears_usd\n"
             f"FROM {W}.monthly_billing b JOIN {W}.water_accounts a ON b.account_id = a.account_id\n"
             f"WHERE b.bill_month = (SELECT MAX(bill_month) FROM {W}.monthly_billing)\n"
             f"GROUP BY a.borough ORDER BY total_arrears_usd DESC"),
            ("Water main breaks per winter by borough",
             f"SELECT CASE WHEN MONTH(break_date) = 12 THEN YEAR(break_date) + 1 ELSE YEAR(break_date) END AS winter_ending,\n"
             f"  borough, COUNT(*) AS breaks\nFROM {W}.water_main_breaks WHERE MONTH(break_date) IN (12, 1, 2)\n"
             f"GROUP BY 1, 2 ORDER BY 1, 3 DESC"),
            ("Average days to close No Water complaints by borough",
             f"SELECT borough, COUNT(*) AS closed_requests, ROUND(AVG(days_to_close), 2) AS avg_days_to_close,\n"
             f"  ROUND(PERCENTILE(days_to_close, 0.9), 2) AS p90_days_to_close\n"
             f"FROM {W}.service_requests_311 WHERE descriptor = 'No Water' AND status = 'Closed'\n"
             f"GROUP BY borough ORDER BY avg_days_to_close DESC"),
            ("System-wide reservoir storage versus normal on the latest date",
             f"SELECT reading_date, ROUND(SUM(storage_bg) / SUM(capacity_bg) * 100, 1) AS systemwide_pct_full,\n"
             f"  ROUND(MAX(normal_pct_full), 1) AS normal_pct_full, MAX(drought_status) AS drought_status\n"
             f"FROM {W}.reservoir_storage WHERE reading_date = (SELECT MAX(reading_date) FROM {W}.reservoir_storage)\n"
             f"GROUP BY reading_date"),
            ("Average monthly bill for 1-3 family homes in FY2026 vs FY2027",
             f"SELECT b.fiscal_year, r.water_rate_per_ccf, ROUND(AVG(b.billed_amount_usd), 2) AS avg_monthly_bill_usd\n"
             f"FROM {W}.monthly_billing b JOIN {W}.water_accounts a ON b.account_id = a.account_id\n"
             f"JOIN {W}.rate_schedules r ON a.rate_code = r.rate_code AND b.fiscal_year = r.fiscal_year\n"
             f"WHERE a.rate_code = 'R1' GROUP BY b.fiscal_year, r.water_rate_per_ccf ORDER BY b.fiscal_year"),
        ],
        "joins": [
            ("monthly_billing", "water_accounts", "`monthly_billing`.`account_id` = `water_accounts`.`account_id`", "MANY_TO_ONE"),
            ("water_accounts", "community_districts", "`water_accounts`.`community_district` = `community_districts`.`community_district`", "MANY_TO_ONE"),
            ("water_main_breaks", "community_districts", "`water_main_breaks`.`community_district` = `community_districts`.`community_district`", "MANY_TO_ONE"),
            ("service_requests_311", "community_districts", "`service_requests_311`.`community_district` = `community_districts`.`community_district`", "MANY_TO_ONE"),
        ],
        "measures": [
            ("systemwide_pct_full", "System-wide reservoir % full", "SUM(reservoir_storage.storage_bg) / SUM(reservoir_storage.capacity_bg) * 100", ["reservoir level", "storage percent"]),
            ("break_count", "Water main breaks", "COUNT(water_main_breaks.break_id)", ["main breaks", "breaks"]),
        ],
        "benchmarks": [
            ("What is total arrears citywide as of the latest bill month?",
             f"SELECT ROUND(SUM(arrears_balance_usd), 0) FROM {W}.monthly_billing WHERE bill_month = (SELECT MAX(bill_month) FROM {W}.monthly_billing)"),
            ("How many accounts are lien-eligible, by borough?",
             f"SELECT borough, COUNT(*) FROM {W}.water_accounts WHERE account_status = 'Lien-Eligible' GROUP BY borough ORDER BY 2 DESC"),
            ("What was the lowest system-wide reservoir level in 2024 and on what date?",
             f"SELECT reading_date, ROUND(SUM(storage_bg) / SUM(capacity_bg) * 100, 1) AS pct FROM {W}.reservoir_storage WHERE YEAR(reading_date) = 2024 GROUP BY reading_date ORDER BY pct ASC LIMIT 1"),
            ("How many water main breaks were on unlined cast iron pipe?",
             f"SELECT COUNT(*) FROM {W}.water_main_breaks WHERE pipe_material = 'Unlined Cast Iron'"),
            ("What were total water and sewer charges billed in FY2026?",
             f"SELECT ROUND(SUM(water_charge_usd), 0) AS water_usd, ROUND(SUM(sewer_charge_usd), 0) AS sewer_usd FROM {W}.monthly_billing WHERE fiscal_year = 2026"),
        ],
    },
}

DOMAINS["health"] = {
    "title": "NYC DOHMH Food Safety & Rodents",
    "description": "NYC Health Department food-safety and rodent-control analytics: restaurant inspections and letter grades, violations, DOHMH closures, and rodent inspections including Rat Mitigation Zones. Synthetic workshop data.",
    "schema": SCHEMA_HEALTH,
    "tables": ["restaurants", "inspections", "violations", "violation_codes", "rodent_inspections", "community_districts"],
    "starter_instructions": "This space covers NYC DOHMH restaurant inspections and rodent control. All data is synthetic.",
    "curated_instructions": (
        "This space covers NYC Department of Health and Mental Hygiene (DOHMH) restaurant inspections and rodent control. All data is synthetic.\n\n"
        "Scores and grades:\n"
        "- Inspection score = total violation points. LOWER IS BETTER. 'Best' means the lowest score; 'worst' means the highest.\n"
        "- Grade bands: 0-13 = A, 14-27 = B, 28+ = C. An initial inspection only issues an A; otherwise the restaurant is re-inspected and graded A/B/C on that score.\n"
        "- A restaurant's CURRENT grade = the grade on its most recent inspection where grade IN ('A','B','C'). Filter to grade IN ('A','B','C') FIRST, take the latest row per camis, and only THEN filter to a specific grade. Never count A-grade inspections as A-grade restaurants.\n"
        "- When comparing places or cuisines on scores, use initial inspections only (inspection_type LIKE '%Initial Inspection'), because re-inspections are only done for restaurants that scored poorly.\n\n"
        "Definitions:\n"
        "- 'Closed', 'shut down' or 'closure' = inspections.action LIKE 'Establishment Closed by DOHMH%'. A C grade is NOT a closure.\n"
        "- 'How many restaurants were closed' = COUNT(DISTINCT camis) of closure inspections; 'how many closures' = number of closure inspections (a restaurant can be closed more than once).\n"
        "- 'Critical violation' = violation_codes.is_critical = TRUE (Critical or Public Health Hazard). 'Mice' / 'roaches' = codes 04L / 04M.\n"
        "- 'Rat activity rate' = share of rodent Initial inspections with result = 'Rat Activity'. Bait and Clean Up visits are treatments, not inspections: exclude them.\n"
        "- 'Rat zones' = rodent_inspections.in_rat_mitigation_zone = TRUE.\n\n"
        "Rules:\n"
        "- Average scores and count inspections from the inspections table. Do NOT join violations for that: it repeats each inspection once per violation.\n"
        "- Show community districts with both code and cd_name (join community_districts).\n"
        "- For scores, grades and closures, prefer the inspection_metrics metric view (query measures with MEASURE())."
    ),
    "sample_questions": [
        "How many restaurant inspections were done each month?",
        "What are the most common violations?",
        "Which cuisines have the highest average inspection scores?",
        "How many restaurants are there in each borough?",
        "Where were the most rodent inspections?",
    ],
    "example_sqls": [
        ("How many restaurants currently hold each letter grade?",
         f"SELECT grade AS current_grade, COUNT(*) AS restaurants\nFROM (SELECT * FROM {H}.inspections WHERE grade IN ('A', 'B', 'C')\n  QUALIFY ROW_NUMBER() OVER (PARTITION BY camis ORDER BY inspection_date DESC, inspection_id DESC) = 1)\nGROUP BY grade ORDER BY grade"),
        ("Which community districts have the best average inspection scores?",
         f"SELECT r.community_district, d.cd_name, COUNT(*) AS initial_inspections, ROUND(AVG(i.score), 1) AS avg_score\n"
         f"FROM {H}.inspections i JOIN {H}.restaurants r ON i.camis = r.camis\n"
         f"JOIN {H}.community_districts d ON r.community_district = d.community_district\n"
         f"WHERE i.inspection_type LIKE '%Initial Inspection'\n"
         f"GROUP BY r.community_district, d.cd_name HAVING COUNT(*) >= 30 ORDER BY AVG(i.score) ASC LIMIT 10"),
        ("How many restaurants currently have an A grade?",
         f"SELECT COUNT(*) AS restaurants_currently_a\nFROM (SELECT * FROM {H}.inspections WHERE grade IN ('A', 'B', 'C')\n"
         f"      QUALIFY ROW_NUMBER() OVER (PARTITION BY camis ORDER BY inspection_date DESC, inspection_id DESC) = 1) latest\n"
         f"WHERE latest.grade = 'A'"),
        ("How many restaurants did DOHMH close in 2025, by borough?",
         f"SELECT r.borough, COUNT(DISTINCT i.camis) AS restaurants_closed, COUNT(*) AS closure_events\nFROM {H}.inspections i JOIN {H}.restaurants r ON i.camis = r.camis\n"
         f"WHERE i.action LIKE 'Establishment Closed by DOHMH%' AND YEAR(i.inspection_date) = 2025\n"
         f"GROUP BY r.borough ORDER BY restaurants_closed DESC"),
        ("What is the rat activity rate by borough in 2025?",
         f"SELECT borough, COUNT(*) AS initial_inspections,\n"
         f"  ROUND(100.0 * COUNT_IF(result = 'Rat Activity') / COUNT(*), 1) AS rat_activity_rate_pct\n"
         f"FROM {H}.rodent_inspections WHERE inspection_type = 'Initial' AND YEAR(inspection_date) = 2025\n"
         f"GROUP BY borough ORDER BY rat_activity_rate_pct DESC"),
        ("What are the most common critical violations?",
         f"SELECT v.violation_code, c.description, c.category, COUNT(*) AS times_cited\n"
         f"FROM {H}.violations v JOIN {H}.violation_codes c ON v.violation_code = c.violation_code\n"
         f"WHERE c.is_critical GROUP BY v.violation_code, c.description, c.category ORDER BY times_cited DESC LIMIT 10"),
    ],
    "joins": [
        ("inspections", "restaurants", "`inspections`.`camis` = `restaurants`.`camis`", "MANY_TO_ONE"),
        ("restaurants", "community_districts", "`restaurants`.`community_district` = `community_districts`.`community_district`", "MANY_TO_ONE"),
        ("violations", "violation_codes", "`violations`.`violation_code` = `violation_codes`.`violation_code`", "MANY_TO_ONE"),
        ("violations", "inspections", "`violations`.`inspection_id` = `inspections`.`inspection_id`", "MANY_TO_ONE"),
        ("rodent_inspections", "community_districts", "`rodent_inspections`.`community_district` = `community_districts`.`community_district`", "MANY_TO_ONE"),
    ],
    "measures": [
        ("avg_initial_score", "Average initial inspection score", "AVG(CASE WHEN inspections.inspection_type LIKE '%Initial Inspection' THEN inspections.score END)", ["average score", "inspection score", "sanitary score"]),
        ("rat_activity_rate", "Rat activity rate", "SUM(CASE WHEN rodent_inspections.inspection_type = 'Initial' AND rodent_inspections.result = 'Rat Activity' THEN 1 ELSE 0 END) / SUM(CASE WHEN rodent_inspections.inspection_type = 'Initial' THEN 1 ELSE 0 END)", ["rat rate", "rat activity", "rodent failure rate"]),
    ],
    "benchmarks": [
        ("How many restaurants are in Queens?",
         f"SELECT COUNT(*) FROM {H}.restaurants WHERE borough = 'Queens'"),
        ("How many DOHMH closures were there in 2025?",
         f"SELECT COUNT(*) FROM {H}.inspections WHERE action LIKE 'Establishment Closed by DOHMH%' AND YEAR(inspection_date) = 2025"),
        ("What share of restaurants currently hold an A grade?",
         f"SELECT ROUND(100.0 * COUNT_IF(grade = 'A') / COUNT(*), 1) AS pct_a FROM (SELECT * FROM {H}.inspections WHERE grade IN ('A', 'B', 'C')\n  QUALIFY ROW_NUMBER() OVER (PARTITION BY camis ORDER BY inspection_date DESC, inspection_id DESC) = 1)"),
        ("What was the rat activity rate on initial rodent inspections in 2025?",
         f"SELECT ROUND(100.0 * COUNT_IF(result = 'Rat Activity') / COUNT(*), 1) FROM {H}.rodent_inspections WHERE inspection_type = 'Initial' AND YEAR(inspection_date) = 2025"),
        ("Which violation code was cited most often?",
         f"SELECT violation_code, COUNT(*) AS n FROM {H}.violations GROUP BY violation_code ORDER BY n DESC LIMIT 1"),
    ],
}

# ---- Trusted assets (Lab 4, core): parameterized example queries. Genie labels answers from these as Trusted.
#      (question, sql with :params, {param: (type, example value used by the self-test)})
DOMAINS["aging"]["trusted"] = (
    "How many isolated frail clients live in a borough?",
    f"SELECT COUNT(*) AS isolated_frail_clients\nFROM {A}.clients\n"
    f"WHERE medically_frail AND living_alone AND enrollment_status <> 'Disenrolled'\n  AND borough = :borough",
    {"borough": ("String", "Brooklyn")})
DOMAINS["transit"]["trusted"] = (
    "What is the farebox recovery ratio for an agency in a given year?",
    f"SELECT a.agency_name, f.calendar_year,\n  ROUND(SUM(f.fare_revenue_m) / SUM(f.total_expense_m), 3) AS farebox_recovery_ratio\n"
    f"FROM {T}.monthly_financials f JOIN {T}.transit_agencies a ON f.agency_id = a.agency_id\n"
    f"WHERE a.agency_name = :agency_name AND f.calendar_year = :year\nGROUP BY a.agency_name, f.calendar_year",
    {"agency_name": ("String", "NYC Transit - Subway"), "year": ("Integer", 2025)})
DOMAINS["water"]["trusted"] = (
    "What is the current arrears balance in a borough?",
    f"SELECT a.borough, COUNT_IF(b.arrears_balance_usd > 0) AS delinquent_accounts,\n  ROUND(SUM(b.arrears_balance_usd), 0) AS current_arrears_usd\n"
    f"FROM {W}.monthly_billing b JOIN {W}.water_accounts a ON b.account_id = a.account_id\n"
    f"WHERE b.bill_month = (SELECT MAX(bill_month) FROM {W}.monthly_billing) AND a.borough = :borough\nGROUP BY a.borough",
    {"borough": ("String", "Bronx")})
DOMAINS["health"]["trusted"] = (
    "How many restaurants in a borough currently hold each letter grade?",
    f"SELECT r.borough, g.grade AS current_grade, COUNT(*) AS restaurants\n"
    f"FROM (SELECT * FROM {H}.inspections WHERE grade IN ('A', 'B', 'C')\n"
    f"      QUALIFY ROW_NUMBER() OVER (PARTITION BY camis ORDER BY inspection_date DESC, inspection_id DESC) = 1) g\n"
    f"JOIN {H}.restaurants r ON g.camis = r.camis\n"
    f"WHERE r.borough = :borough\nGROUP BY r.borough, g.grade ORDER BY g.grade",
    {"borough": ("String", "Manhattan")})

# ---- Metric views (Lab 4 step 6). One per domain; each turns the definition traps into governed UC measures. ----
DOMAINS["aging"]["metric_view"] = ("client_metrics", f"""version: 1.1
source: {A}.clients
comment: "Client counts and frailty KPIs for NYC aging and home-care clients (excludes disenrolled clients)."
filter: enrollment_status <> 'Disenrolled'
joins:
  - name: dim_district
    source: {A}.community_districts
    'on': source.community_district = dim_district.community_district
  - name: dim_plan
    source: {A}.mltc_plans
    'on': source.plan_id = dim_plan.plan_id
dimensions:
  - name: Borough
    expr: source.borough
  - name: Community District
    expr: CONCAT(source.community_district, ' ', dim_district.cd_name)
    comment: "Community district code and neighborhood name, e.g. BK05 East New York / Starrett City."
  - name: Coverage Type
    expr: source.coverage_type
  - name: MLTC Plan
    expr: dim_plan.plan_name
  - name: Primary Language
    expr: source.primary_language
  - name: Age Group
    expr: CASE WHEN source.age < 65 THEN 'Under 65' WHEN source.age < 75 THEN '65-74' WHEN source.age < 85 THEN '75-84' ELSE '85+' END
measures:
  - name: Clients
    expr: COUNT(1)
  - name: Frail Clients
    expr: COUNT(1) FILTER (WHERE source.medically_frail)
    synonyms: [frail, medically frail, frail older adults]
  - name: Isolated Frail Clients
    expr: COUNT(1) FILTER (WHERE source.medically_frail AND source.living_alone)
    comment: "Agency definition of isolated: medically frail AND living alone."
    synonyms: [isolated, isolated frail older adults, at risk of isolation, frail living alone]
  - name: Frail Share
    expr: MEASURE(`Frail Clients`) / MEASURE(`Clients`)
    format:
      type: percentage
      decimal_places:
        type: max
        places: 1
""", f"""SELECT `Community District`, MEASURE(`Isolated Frail Clients`) AS isolated_frail
FROM {A}.client_metrics
GROUP BY ALL ORDER BY isolated_frail DESC LIMIT 10""")

DOMAINS["transit"]["metric_view"] = ("transit_operating_metrics", f"""version: 1.1
source: {T}.monthly_financials
comment: "Monthly transit operating finance KPIs. All dollar measures are millions of USD."
joins:
  - name: dim_agency
    source: {T}.transit_agencies
    'on': source.agency_id = dim_agency.agency_id
dimensions:
  - name: Month
    expr: source.month
  - name: Calendar Year
    expr: source.calendar_year
    comment: "The MTA fiscal year equals the calendar year."
  - name: Agency
    expr: dim_agency.agency_name
    comment: "Agency NAME, e.g. 'NYC Transit - Subway', 'Staten Island Ferry'. Use Agency ID to filter by code."
  - name: Agency ID
    expr: source.agency_id
    comment: "Agency code: NYCT-SUB, NYCT-BUS, MTABC, SIR, LIRR, MNR, AAR, SIF, NYCF."
  - name: Operator
    expr: dim_agency.operator
  - name: Service Group
    expr: CASE source.agency_id WHEN 'NYCT-SUB' THEN 'Subway' WHEN 'NYCT-BUS' THEN 'Buses' WHEN 'MTABC' THEN 'Buses' WHEN 'LIRR' THEN 'Commuter Rail' WHEN 'MNR' THEN 'Commuter Rail' WHEN 'SIF' THEN 'Ferries' WHEN 'NYCF' THEN 'Ferries' WHEN 'AAR' THEN 'Paratransit' ELSE 'Staten Island Railway' END
    comment: "Agency definition: Buses = NYC Transit Bus + MTA Bus Company; Commuter Rail = LIRR + Metro-North; Ferries = Staten Island Ferry + NYC Ferry."
    synonyms: [the buses, mode group, service]
measures:
  - name: Fare Revenue
    expr: SUM(source.fare_revenue_m)
    comment: "Passenger fare revenue, millions USD."
  - name: Total Expense
    expr: SUM(source.total_expense_m)
    comment: "Total operating expense, millions USD."
    synonyms: [cost, spend, operating cost]
  - name: Operating Balance
    expr: SUM(source.operating_balance_m)
    comment: "Revenue minus expense, millions USD. Negative = deficit / loss."
    synonyms: [deficit, surplus, loss, net operating result]
  - name: Public Operating Support
    expr: SUM(source.dedicated_taxes_m + source.state_city_subsidy_m + source.federal_funds_m)
    comment: "Dedicated taxes + state/city subsidies + federal operating aid, millions USD. Congestion pricing is NOT included: it funds capital."
    synonyms: [subsidy, public subsidy]
  - name: Farebox Recovery Ratio
    expr: SUM(source.fare_revenue_m) FILTER (WHERE source.agency_id <> 'SIF') / SUM(source.total_expense_m) FILTER (WHERE source.agency_id <> 'SIF')
    comment: "Fare revenue / operating expense, weighted correctly across agencies and months. Excludes the fare-free Staten Island Ferry by policy, so it is NULL for SIF: drop NULLs when ranking."
    synonyms: [farebox, farebox recovery, fare recovery]
    format:
      type: percentage
      decimal_places:
        type: max
        places: 1
""", f"""SELECT `Agency`, MEASURE(`Farebox Recovery Ratio`) AS farebox_recovery
FROM {T}.transit_operating_metrics
WHERE `Calendar Year` = 2025 AND `Agency` <> 'Staten Island Ferry'
GROUP BY ALL ORDER BY farebox_recovery ASC""")

DOMAINS["water"]["metric_view"] = ("water_billing_metrics", f"""version: 1.1
source: |
  SELECT b.account_id, b.bill_month, b.fiscal_year, b.consumption_ccf, b.water_charge_usd, b.sewer_charge_usd,
         b.billed_amount_usd, b.paid_amount_usd, b.arrears_balance_usd,
         a.borough, a.community_district, a.rate_code, a.account_status,
         COALESCE(a.assistance_program, 'None') AS assistance_program,
         b.bill_month = MAX(b.bill_month) OVER () AS is_latest_month
  FROM {W}.monthly_billing b JOIN {W}.water_accounts a ON b.account_id = a.account_id
comment: "Water and sewer billing, payments and arrears KPIs. NYC fiscal year runs July-June. Arrears measures are a snapshot as of the latest bill month."
dimensions:
  - name: Bill Month
    expr: bill_month
  - name: Fiscal Year
    expr: fiscal_year
    comment: "NYC fiscal year (FY2026 = Jul 2025 - Jun 2026)."
    synonyms: [FY]
  - name: Borough
    expr: borough
  - name: Community District
    expr: community_district
  - name: Rate Class
    expr: CASE rate_code WHEN 'R1' THEN '1-3 Family Residential' WHEN 'MF' THEN 'Multifamily (Metered)' WHEN 'MCP' THEN 'Multifamily Conservation Program' WHEN 'CM' THEN 'Commercial' ELSE 'Industrial' END
  - name: Assistance Program
    expr: assistance_program
  - name: Account Status
    expr: account_status
measures:
  - name: Total Billed
    expr: SUM(billed_amount_usd)
    comment: "Water + sewer charges billed, USD."
    synonyms: [charges, billings, water and sewer charges]
  - name: Water Charges
    expr: SUM(water_charge_usd)
  - name: Sewer Charges
    expr: SUM(sewer_charge_usd)
  - name: Payments
    expr: SUM(paid_amount_usd)
  - name: Consumption CCF
    expr: SUM(consumption_ccf)
    comment: "Water use in ccf (1 ccf = 748 gallons)."
  - name: Current Arrears
    expr: SUM(arrears_balance_usd) FILTER (WHERE is_latest_month)
    comment: "Outstanding unpaid balance as of the latest bill month, USD. A snapshot: never summed across months."
    synonyms: [arrears, debt, outstanding balance, unpaid balance, total arrears]
  - name: Delinquent Accounts
    expr: COUNT(DISTINCT account_id) FILTER (WHERE is_latest_month AND arrears_balance_usd > 0)
    comment: "Agency definition: accounts with an unpaid balance in the latest bill month."
    synonyms: [delinquent, accounts in arrears, past due accounts]
""", f"""SELECT `Borough`, MEASURE(`Current Arrears`) AS current_arrears, MEASURE(`Delinquent Accounts`) AS delinquent_accounts
FROM {W}.water_billing_metrics
GROUP BY ALL ORDER BY current_arrears DESC""")

DOMAINS["health"]["metric_view"] = ("inspection_metrics", f"""version: 1.1
source: {H}.inspections
comment: "Restaurant inspection KPIs for NYC DOHMH. Inspection scores: lower is better."
joins:
  - name: dim_restaurant
    source: {H}.restaurants
    'on': source.camis = dim_restaurant.camis
dimensions:
  - name: Inspection Month
    expr: DATE_TRUNC('MONTH', source.inspection_date)
  - name: Inspection Year
    expr: YEAR(source.inspection_date)
  - name: Inspection Type
    expr: source.inspection_type
  - name: Borough
    expr: dim_restaurant.borough
  - name: Community District
    expr: dim_restaurant.community_district
  - name: Cuisine
    expr: dim_restaurant.cuisine
  - name: Chain
    expr: CASE WHEN dim_restaurant.is_chain THEN 'Chain' ELSE 'Independent' END
measures:
  - name: Inspections
    expr: COUNT(1)
  - name: Restaurants Inspected
    expr: COUNT(DISTINCT source.camis)
  - name: Average Initial Score
    expr: AVG(source.score) FILTER (WHERE source.inspection_type LIKE '%Initial Inspection')
    comment: "Average score on initial inspections only (re-inspections are biased toward poor performers). Lower is better."
    synonyms: [average score, inspection score, sanitary score]
  - name: Grade A Rate
    expr: COUNT(1) FILTER (WHERE source.grade = 'A') / COUNT(1) FILTER (WHERE source.grade IN ('A', 'B', 'C'))
    comment: "Share of letter grades issued that were A."
    synonyms: [A rate, share of A grades]
    format:
      type: percentage
      decimal_places:
        type: max
        places: 1
  - name: Closures
    expr: COUNT(1) FILTER (WHERE source.action LIKE 'Establishment Closed by DOHMH%')
    comment: "Number of closure events (inspections where DOHMH closed the restaurant). A C grade is not a closure."
    synonyms: [closure events, number of closures, shutdowns]
  - name: Restaurants Closed
    expr: COUNT(DISTINCT source.camis) FILTER (WHERE source.action LIKE 'Establishment Closed by DOHMH%')
    comment: "Distinct restaurants DOHMH closed at least once. Use for 'how many restaurants were closed / shut down'."
    synonyms: [restaurants shut down, restaurants closed by DOHMH, closed restaurants]
  - name: Average Score
    expr: AVG(source.score)
    comment: "Average score across all inspections. Lower is better. Prefer Average Initial Score when comparing places or cuisines."
  - name: Critical Violations
    expr: SUM(source.critical_violation_count)
    synonyms: [critical, critical flags]
""", f"""SELECT `Borough`, MEASURE(`Average Initial Score`) AS avg_initial_score, MEASURE(`Closures`) AS closures
FROM {H}.inspection_metrics
WHERE `Inspection Year` = 2025
GROUP BY ALL ORDER BY avg_initial_score ASC""")

# COMMAND ----------

import json
import uuid
import requests

ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
TOKEN = ctx.apiToken().get()
HOST = ctx.apiUrl().get()
HDRS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

try:
    me = requests.get(f"{HOST}/api/2.0/preview/scim/v2/Me", headers=HDRS, timeout=30).json()
except Exception:
    me = {}
USER = me.get("userName", "")
PARENT_PATH = f"/Users/{USER}" if USER else "/Users"
print(f"Genie spaces live under: {PARENT_PATH}")


def detect_warehouse():
    """Pick a SQL warehouse: prefer a running serverless one (Free Edition has exactly one)."""
    r = requests.get(f"{HOST}/api/2.0/sql/warehouses", headers=HDRS, timeout=60)
    r.raise_for_status()
    whs = r.json().get("warehouses", [])
    if not whs:
        raise RuntimeError("No SQL warehouse found. Create one under SQL Warehouses, or paste its ID into the warehouse_id widget.")
    whs.sort(key=lambda w: (w.get("state") != "RUNNING", not w.get("enable_serverless_compute", False)))
    print(f"Using SQL warehouse: {whs[0].get('name')} ({whs[0]['id']})")
    return whs[0]["id"]


def _hid():
    """Genie serialized_space element ids must be 32-hex-char UUIDs (no hyphens)."""
    return uuid.uuid4().hex


def _by_id(items):
    return sorted(items, key=lambda e: e["id"])


def build_serialized_space(dom, curated):
    # serialized_space v2 rules: string fields are ARRAYS; ids are hyphen-less hex; every id-keyed
    # list is sorted by id; tables sorted by identifier; at most one text_instructions entry.
    fq = lambda t: f"{CATALOG}.{dom['schema']}.{t}"
    space = {
        "version": 2,
        "config": {"sample_questions": _by_id([{"id": _hid(), "question": [q]} for q in dom["sample_questions"]])},
        "data_sources": {"tables": [{"identifier": t} for t in sorted(fq(t) for t in dom["tables"])]},
        "instructions": {"text_instructions": [{
            "id": _hid(), "content": [dom["curated_instructions"] if curated else dom["starter_instructions"]]}]},
    }
    if curated:
        space["data_sources"]["metric_views"] = [{"identifier": fq(dom["metric_view"][0])}]
        ins = space["instructions"]
        ins["example_question_sqls"] = _by_id([{"id": _hid(), "question": [q], "sql": [s]} for q, s in dom["example_sqls"]])
        ins["join_specs"] = _by_id([{
            "id": _hid(),
            "left": {"identifier": fq(l), "alias": l},
            "right": {"identifier": fq(r), "alias": r},
            "sql": [cond, f"--rt=FROM_RELATIONSHIP_TYPE_{rt}--"],
        } for l, r, cond, rt in dom["joins"]])
        ins["sql_snippets"] = {"measures": _by_id([{
            "id": _hid(), "alias": alias, "display_name": name, "sql": [sql], "synonyms": syn,
        } for alias, name, sql, syn in dom["measures"]])}
        space["benchmarks"] = {"questions": _by_id([{
            "id": _hid(), "question": [q], "answer": [{"format": "SQL", "content": [s]}],
        } for q, s in dom["benchmarks"]])}
    return json.dumps(space)


def list_spaces():
    out, token = {}, None
    while True:
        params = {"page_size": 100, **({"page_token": token} if token else {})}
        r = requests.get(f"{HOST}/api/2.0/genie/spaces", headers=HDRS, params=params, timeout=60)
        r.raise_for_status()
        j = r.json()
        for s in j.get("spaces", []):
            out.setdefault(s.get("title"), s.get("space_id"))
        token = j.get("next_page_token")
        if not token:
            return out


def upsert_space(title, description, serialized, existing):
    body = {"serialized_space": serialized, "warehouse_id": WAREHOUSE_ID, "title": title, "description": description}
    if title in existing:
        sid = existing[title]
        r = requests.patch(f"{HOST}/api/2.0/genie/spaces/{sid}", headers=HDRS, data=json.dumps(body), timeout=120)
        verb = "updated"
    else:
        r = requests.post(f"{HOST}/api/2.0/genie/spaces", headers=HDRS,
                          data=json.dumps({**body, "parent_path": PARENT_PATH}), timeout=120)
        verb = "created"
        sid = r.json().get("space_id") if r.status_code < 300 else None
    if r.status_code >= 300:
        print(f"  ✗ {title} -> {r.status_code}: {r.text[:500]}")
        return None
    print(f"  ✓ {verb}: {title}\n      {HOST}/genie/rooms/{sid}")
    if SHARE_GROUP:
        p = requests.patch(f"{HOST}/api/2.0/permissions/genie/{sid}", headers=HDRS, timeout=60,
                           data=json.dumps({"access_control_list": [{"group_name": SHARE_GROUP, "permission_level": "CAN_RUN"}]}))
        print(f"      shared with {SHARE_GROUP}: {'ok' if p.status_code < 300 else p.text[:200]}")
    return sid

# COMMAND ----------

# MAGIC %md ### Create or update the Curated spaces

# COMMAND ----------

SPACE_IDS = {}
if GENIE_MODE != "none":
    try:
        if not WAREHOUSE_ID:
            WAREHOUSE_ID = detect_warehouse()
        existing = list_spaces()
    except Exception as e:
        print(f"Could not reach the Genie API ({str(e)[:200]}).\n"
              "That's OK: the data and metric views are ready. Build your Genie space by hand (workshop Lab 1).")
        GENIE_MODE = "none"
if GENIE_MODE != "none":
    variants = {"both": [False, True], "starter": [False], "curated": [True]}[GENIE_MODE]
    for key, dom in DOMAINS.items():
        for curated in variants:
            title = f"{dom['title']} ({'Curated' if curated else 'Starter'})"
            SPACE_IDS[title] = upsert_space(title, dom["description"], build_serialized_space(dom, curated), existing)
    if SHARE_GROUP:
        requests.patch(f"{HOST}/api/2.0/permissions/sql/warehouses/{WAREHOUSE_ID}", headers=HDRS, timeout=60,
                       data=json.dumps({"access_control_list": [{"group_name": SHARE_GROUP, "permission_level": "CAN_USE"}]}))
    print(json.dumps(SPACE_IDS, indent=2))
else:
    print("Skipped Genie space creation (genie_spaces = none).")

