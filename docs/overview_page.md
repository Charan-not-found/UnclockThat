# CLOCKIT Overview Page Reference

**Source Component:** `frontend/src/pages/Dashboard/Dashboard.tsx`  
**Route:** `/` (Overview)  
**Data Policy:** All metrics, charts, and tables are computed live from persisted database records via backend APIs (no mock data).

---

## 1. Header & Global Controls

- **Title:** `Overview`
- **Subtitle:** `Live metrics from <total> persisted inspection record(s) · last 30 days`
- **Help Legend (`?` button via `PageHelpLegend`):**
  - **Pass Rate:** Percentage of inspections with `PASS` (`Completed`) decision.
  - **Anomaly Rate:** Percentage of inspections flagged as `Failed` (`FAIL`) or `Needs review` (`REVIEW_REQUIRED`).
  - **Severity:** `Critical`, `Major`, `Minor`, and `Informational` severity levels.
- **Refresh Button:** Re-fetches all 4 Overview API calls in parallel (`listInspections`, `getSummary`, `getTrend`, `getSeverityDistribution`).

---

## 2. Top KPI Stat Cards (4 Cards, 30-Day Window)

Data source: `GET /api/v1/analytics/summary?days=30`

| Card | Value Displayed | Hint / Subtext | Accent Rules | Backend Calculation |
| :--- | :--- | :--- | :--- | :--- |
| **Total Inspections** | `total_inspections` (integer) | — | Default | Count of `InspectionRecord` rows within the last 30 days. |
| **Pass Rate (30d)** | `<pass_rate_pct>%` (or `—` if 0 inspections) | `"No inspections yet"` if 0, else `"<pass_count> passed"` | Green if `>= 80%`, Red if `< 80%`, Default if `null` | `round(pass_count / total * 100, 1)` where `overall_decision == "PASS"`. |
| **Anomaly Rate (30d)** | `<anomaly_rate_pct>%` (or `—` if 0 inspections) | `"<fail_count> failed"` | Red if `> 20%`, Default otherwise | `round((fail_count + review_count) / total * 100, 1)` where `overall_decision` is `"FAIL"` or `"REVIEW_REQUIRED"`. |
| **Awaiting Review** | `review_count` (integer) | — | Amber if `> 0`, Green if `0` | Count of records with `overall_decision == "REVIEW_REQUIRED"`. |

---

## 3. Charts Section

### A. Inspection Trend — Last 7 Days (Line Chart)
Data source: `GET /api/v1/analytics/trend?days=7`

- **Subtitle:** `Source: persisted inspection records. Daily counts.`
- **X-Axis:** `day` formatted as `"<Weekday> <DD>"` (e.g., `Thu 26`) for each of the last 7 UTC days.
- **Y-Axis:** Integer counts (`allowDecimals={false}`).
- **Series Plotted:**
  1. **Inspections** (`dataKey="inspections"`, solid blue `#2563eb`) — total inspections on that day.
  2. **Anomalies / Fails** (`dataKey="anomalies"`, solid red `#dc2626`) — records with `overall_decision == "FAIL"`.
  3. **Needs review** (`dataKey="reviews"`, dashed amber `#d97706`) — records with `overall_decision == "REVIEW_REQUIRED"`.
- **Empty State:** `"No inspection data yet — Run your first inspection to see trends here."`

### B. Severity Distribution — Last 30 Days (Donut / Pie Chart + Breakdown List)
Data source: `GET /api/v1/analytics/severity-distribution?days=30`

- **Subtitle:** `From severity_scores table.`
- **Chart:** Donut chart (`innerRadius={30}`, `outerRadius={58}`) grouped by `severity_level` from `SeverityScore` rows belonging to inspections in the last 30 days.
- **Severity Colors & Legend List:**
  - `Critical`: `#dc2626` (Red) + count
  - `Major`: `#d97706` (Amber/Orange) + count
  - `Minor`: `#ca8a04` (Yellow) + count
  - `Informational`: `#6b7280` (Gray) + count
- **Empty State:** `"No severity data — Severity distribution appears after inspections."`

---

## 4. Recent Inspections Table

Data source: `GET /api/v1/inspections?limit=20` (displays up to the **8 most recent** rows)

- **Header Action:** `View all →` link to `/history` (Inspection History page).
- **Columns:**
  1. **ID** — Monospace clickable link (`INS-<id>`) navigating to `/inspections/<id>` (Inspection Detail).
  2. **Product** — `product_serial` / scanned product name.
  3. **Industry** — Manufacturer/Scanner Unit industry.
  4. **Status** — Mapped `StatusBadge` (`Completed`, `Needs review`, `Failed`).
  5. **Severity** — `StatusBadge` (`Critical`, `Major`, `Minor`, `Informational`).
  6. **Score** — `quality_score` (0–100 integer).
  7. **Date** — Localized date string (`new Date(r.date).toLocaleDateString()`).
- **Empty State:** `"No inspections yet — Submit your first test sample to populate this table."` with a `"Go to Test Sample →"` link to `/test-sample`.

---

## 5. Loading & Error States

- **Loading:** Spinner with `"Loading dashboard…"`.
- **Error:** `"Couldn't load dashboard data"` (`"Check that the backend is running on port 8000."`) with a **Retry** button.
