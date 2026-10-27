"""Query the generated tables for the Lab 3 trap answers and write answers.json.

Usage: python3 compute_answers.py <profile> <warehouse_id> <catalog>
"""
import json
import subprocess
import sys

PROFILE, WH, CAT = sys.argv[1:4]
A, T, W = f"{CAT}.nyc_aging_home_care", f"{CAT}.nyc_transit_finance", f"{CAT}.nyc_dep_water"
H = f"{CAT}.nyc_dohmh_food_safety"


def q(sql):
    body = json.dumps({"statement": sql, "warehouse_id": WH, "wait_timeout": "50s"})
    out = subprocess.run(["databricks", "api", "post", "/api/2.0/sql/statements", "--json", body, "--profile", PROFILE],
                         capture_output=True, text=True, check=True).stdout
    r = json.loads(out)
    if r["status"]["state"] != "SUCCEEDED":
        raise RuntimeError(f"{sql}\n{r['status']}")
    return r["result"]["data_array"][0]


usd = lambda v: f"${float(v):,.0f}"
pct = lambda v: f"{float(v):.1f}%"
ans = {}

n, k = q(f"""SELECT COUNT(*), SUM(CAST(meets_min_adl_need AS INT)) FROM (SELECT * FROM {A}.functional_assessments
  QUALIFY ROW_NUMBER() OVER (PARTITION BY client_id ORDER BY assessment_date DESC) = 1)""")
ans["aging_assessed"] = f"{int(n):,}"
ans["aging_minadl_pct"] = pct(100 * int(k) / int(n))
ans["aging_minadl_pct_naive"] = pct(q(f"SELECT AVG(CAST(meets_min_adl_need AS INT)) * 100 FROM {A}.functional_assessments")[0])
code, name, c = q(f"""SELECT c.community_district, d.cd_name, COUNT(*) n FROM {A}.clients c JOIN {A}.community_districts d
  ON c.community_district = d.community_district WHERE c.medically_frail AND c.living_alone AND c.enrollment_status <> 'Disenrolled'
  GROUP BY 1, 2 ORDER BY n DESC LIMIT 1""")
ans["aging_isolated_top"] = f"{code} {name} ({c} clients)"
b, r = q(f"""WITH pop AS (SELECT borough, SUM(population) p FROM {A}.community_districts GROUP BY borough),
  f AS (SELECT borough, COUNT(*) n FROM {A}.clients WHERE medically_frail GROUP BY borough)
  SELECT pop.borough, ROUND(f.n * 10000.0 / pop.p, 2) r FROM pop JOIN f USING (borough) ORDER BY r DESC LIMIT 1""")
ans["aging_rate_top"] = f"{b}, {r} frail clients per 10,000 residents"
ans["aging_latest_cost"] = usd(q(f"SELECT SUM(cost_usd) FROM {A}.home_care_services WHERE service_month = DATE'2026-09-01'")[0])

w, nv = q(f"""SELECT SUM(f.fare_revenue_m) / SUM(f.total_expense_m), AVG(f.farebox_recovery_ratio) FROM {T}.monthly_financials f
  JOIN {T}.transit_agencies a USING (agency_id) WHERE a.operator = 'MTA' AND f.calendar_year = 2025""")
ans["tr_fbr_weighted"] = f"{float(w):.3f} ({100*float(w):.1f}%)"
ans["tr_fbr_naive"] = f"{float(nv):.3f} ({100*float(nv):.1f}%)"
nm, r = q(f"""SELECT a.agency_name, SUM(f.fare_revenue_m) / SUM(f.total_expense_m) r FROM {T}.monthly_financials f
  JOIN {T}.transit_agencies a USING (agency_id) WHERE f.agency_id <> 'SIF' GROUP BY 1 ORDER BY r ASC LIMIT 1""")
ans["tr_fbr_worst"] = f"{nm} ({100*float(r):.1f}%, all months)"
ans["tr_cbd_net"] = f"${float(q(f'SELECT SUM(net_revenue_m) FROM {T}.cbd_toll_program')[0]):,.1f} million"
ans["tr_sub_rev"] = f"{float(q(f'''SELECT SUM(total_revenue_m) FROM {T}.monthly_financials WHERE agency_id = 'NYCT-SUB' AND calendar_year = 2025''')[0]):,.0f}"

good = float(q(f"SELECT SUM(arrears_balance_usd) FROM {W}.monthly_billing WHERE bill_month = (SELECT MAX(bill_month) FROM {W}.monthly_billing)")[0])
bad = float(q(f"SELECT SUM(arrears_balance_usd) FROM {W}.monthly_billing")[0])
ans["w_arrears_correct"], ans["w_arrears_naive"], ans["w_arrears_x"] = usd(good), usd(bad), f"{bad/good:.1f}"
ans["w_fy26_billed"] = usd(q(f"SELECT SUM(billed_amount_usd) FROM {W}.monthly_billing WHERE fiscal_year = 2026")[0])
d, p = q(f"""SELECT reading_date, ROUND(SUM(storage_bg) / SUM(capacity_bg) * 100, 1) p FROM {W}.reservoir_storage
  WHERE reading_date BETWEEN DATE'2024-07-01' AND DATE'2025-03-31' GROUP BY reading_date ORDER BY p ASC LIMIT 1""")
ans["w_res_low"] = f"{p}% system-wide on {d}"

ans["w_delinquent"] = f"{int(q(f'SELECT COUNT_IF(arrears_balance_usd > 0) FROM {W}.monthly_billing WHERE bill_month = (SELECT MAX(bill_month) FROM {W}.monthly_billing)')[0]):,}"
ans["w_delinquent_status"] = f"{int(q(f"SELECT COUNT(*) FROM {W}.water_accounts WHERE account_status IN ('Payment Agreement', 'Lien-Eligible')")[0]):,}"
ans["w_last_winter"] = f"{int(q(f"SELECT COUNT(*) FROM {W}.water_main_breaks WHERE break_date BETWEEN DATE'2025-12-01' AND DATE'2026-02-28'")[0]):,}"
ans["aging_hc_wait"] = f"{int(q(f"SELECT waitlist FROM {A}.aging_programs WHERE program_name = 'EISEP Home Care'")[0]):,}"
ans["aging_all_wait"] = f"{int(q(f'SELECT SUM(waitlist) FROM {A}.aging_programs')[0]):,}"
LATEST_H = f"""(SELECT * FROM {H}.inspections WHERE grade IN ('A', 'B', 'C')
  QUALIFY ROW_NUMBER() OVER (PARTITION BY camis ORDER BY inspection_date DESC, inspection_id DESC) = 1)"""
n_a, n_all = q(f"SELECT COUNT_IF(grade = 'A'), COUNT(*) FROM {LATEST_H}")
ans["h_current_a"] = f"{int(n_a):,}"
ans["h_current_a_pct"] = pct(100 * int(n_a) / int(n_all))
ans["h_naive_a"] = f"{int(q(f"SELECT COUNT(*) FROM {H}.inspections WHERE grade = 'A'")[0]):,}"
code, name, sc = q(f"""SELECT r.community_district, d.cd_name, ROUND(AVG(i.score), 1) FROM {H}.inspections i
  JOIN {H}.restaurants r ON i.camis = r.camis JOIN {H}.community_districts d ON r.community_district = d.community_district
  WHERE i.inspection_type LIKE '%Initial Inspection' GROUP BY 1, 2 HAVING COUNT(*) >= 30 ORDER BY AVG(i.score) ASC LIMIT 1""")
ans["h_best_cd"] = f"{code} {name} (average initial score {sc})"
code, name, sc = q(f"""SELECT r.community_district, d.cd_name, ROUND(AVG(i.score), 1) FROM {H}.inspections i
  JOIN {H}.restaurants r ON i.camis = r.camis JOIN {H}.community_districts d ON r.community_district = d.community_district
  WHERE i.inspection_type LIKE '%Initial Inspection' GROUP BY 1, 2 HAVING COUNT(*) >= 30 ORDER BY AVG(i.score) DESC LIMIT 1""")
ans["h_worst_cd"] = f"{code} {name} ({sc})"
ans["h_closures_2025"] = f"{int(q(f"SELECT COUNT(*) FROM {H}.inspections WHERE action LIKE 'Establishment Closed by DOHMH%' AND YEAR(inspection_date) = 2025")[0]):,}"
ans["h_closed_restaurants_2025"] = f"{int(q(f"SELECT COUNT(DISTINCT camis) FROM {H}.inspections WHERE action LIKE 'Establishment Closed by DOHMH%' AND YEAR(inspection_date) = 2025")[0]):,}"
ans["h_avg_score_initial"] = f"{float(q(f"SELECT AVG(score) FROM {H}.inspections WHERE inspection_type LIKE '%Initial Inspection'")[0]):.1f}"
ans["h_c_grades_2025"] = f"{int(q(f"SELECT COUNT(*) FROM {H}.inspections WHERE grade = 'C' AND YEAR(inspection_date) = 2025")[0]):,}"
ans["h_rat_rate"] = pct(q(f"SELECT 100.0 * COUNT_IF(result = 'Rat Activity') / COUNT(*) FROM {H}.rodent_inspections WHERE inspection_type = 'Initial' AND YEAR(inspection_date) = 2025")[0])
ans["h_rat_rate_naive"] = pct(q(f"SELECT 100.0 * COUNT_IF(result = 'Rat Activity') / COUNT(*) FROM {H}.rodent_inspections WHERE YEAR(inspection_date) = 2025")[0])
good = float(q(f"SELECT AVG(score) FROM {H}.inspections")[0])
bad = float(q(f"SELECT AVG(i.score) FROM {H}.inspections i JOIN {H}.violations v ON i.inspection_id = v.inspection_id")[0])
ans["h_avg_score"], ans["h_avg_score_fanout"] = f"{good:.1f}", f"{bad:.1f}"
json.dump(ans, open("answers.json", "w"), indent=1)
print(json.dumps(ans, indent=1))
