# PROMETHEUS-X — Overview Dashboard
## Product & UI Implementation Specification

**Component:** `frontend/src/pages/Dashboard/Dashboard.tsx`  
**Route:** `/`  
**Purpose:** Real-time operational overview of industrial quality inspections.

---

# 1. Design Philosophy

The Overview page is the operational command centre of PROMETHEUS-X.

It should answer four questions immediately:

1. How many products have been inspected?
2. How many products passed quality inspection?
3. How many products have defects or require attention?
4. What are the most recent inspection results?

### Design principles

- Industrial-grade appearance, not a generic SaaS dashboard.
- High information density without visual clutter.
- Clear distinction between normal operations and problems.
- Consistent severity and status colors throughout the application.
- Every important metric should be traceable to actual inspection records.
- No mock data, fabricated statistics, or decorative metrics.
- All dashboard information must come from persisted backend records.

### Visual direction

Use a clean industrial analytics interface:

- Neutral dark or light application theme, consistent with global PROMETHEUS-X styling.
- Restrained use of red, amber, yellow, and green for operational statuses.
- Subtle borders and background separation.
- Compact typography and well-aligned numerical values.
- Avoid excessive gradients, shadows, animations, and oversized cards.

---

# 2. Page Structure

The page should follow this hierarchy:

1. Page Header
2. KPI Overview
3. Inspection Analytics
4. Recent Inspections

Maintain consistent spacing between sections.

---

# 3. Header

### Title
`Overview`

### Subtitle
`Live inspection performance and quality analytics`

Display additional metadata:

- Total persisted inspections.
- Reporting period: Last 30 days.
- Last successful data refresh timestamp.

Example:

`248 inspection records · Last 30 days · Updated 06:24 AM`

### Header Actions

**Refresh Button**
- Re-fetch all four Overview API requests.
- Execute requests concurrently.
- Display a loading indicator while refreshing.
- Prevent duplicate refresh requests.
- Preserve existing dashboard data if a refresh fails.
- Display the last successful refresh time.

**Help Button (?)**

Display definitions for:

| Metric | Definition |
|---|---|
| Pass Rate | Percentage of inspections with a PASS decision. |
| Anomaly Rate | Percentage of inspections with FAIL or REVIEW_REQUIRED decisions. |
| Critical | Highest severity classification. |
| Major | Significant defect classification. |
| Minor | Lower-severity defect classification. |
| Informational | Non-critical observation. |

---

# 4. KPI Overview

**Data source:**

`GET /api/v1/analytics/summary?days=30`

Display four KPI cards.

## Card 1 — Total Inspections

**Primary value:** `total_inspections`

**Description:** Total number of inspection records during the last 30 days.

**Visual treatment:** Neutral.

## Card 2 — Pass Rate

**Primary value:** `pass_rate_pct%`

**Supporting information:** `<pass_count> products passed`

**Calculation:**

`(pass_count / total_inspections) × 100`

Round to one decimal place.

**Accent rules:**
- Green: >= 80%
- Red: < 80%
- Neutral: No inspection records.

## Card 3 — Anomaly Rate

**Primary value:** `anomaly_rate_pct%`

**Supporting information:** `<fail_count> failed`

**Calculation:**

`((fail_count + review_count) / total_inspections) × 100`

Round to one decimal place.

**Accent rules:**
- Red: > 20%
- Neutral: <= 20%
- Neutral: No inspection records.

## Card 4 — Awaiting Review

**Primary value:** `review_count`

**Supporting information:** Inspections requiring operator attention.

**Accent rules:**
- Amber: Greater than zero.
- Green: Zero.

### KPI Behaviour

- Clicking Total Inspections navigates to inspection history.
- Clicking Pass Rate filters history to PASS.
- Clicking Anomaly Rate filters history to FAIL and REVIEW_REQUIRED.
- Clicking Awaiting Review filters history to REVIEW_REQUIRED.

Only implement filtered navigation if the History page supports these filters.

### Zero-data behaviour

Never display fabricated values.

When there are no records:

- Total Inspections: `0`
- Pass Rate: `—`
- Anomaly Rate: `—`
- Awaiting Review: `0`

---

# 5. Inspection Analytics

Use a two-column layout on desktop and a single-column layout on smaller screens.

## A. Inspection Trend

**Data source:**

`GET /api/v1/analytics/trend?days=7`

**Title:** Inspection Activity

**Subtitle:** Daily inspection volume and quality outcomes.

### Chart Type

Multi-series line chart.

### X-axis

Last seven UTC calendar days.

Display labels in a readable format:

`Thu 26`, `Fri 27`, etc.

### Y-axis

Integer inspection counts.

Do not allow decimal tick values.

### Series

1. **Total Inspections**
   - Field: `inspections`
   - Color: Blue.
   - Solid line.

2. **Failed Inspections**
   - Field: `anomalies`
   - Color: Red.
   - Solid line.

3. **Needs Review**
   - Field: `reviews`
   - Color: Amber.
   - Dashed line.

### Interaction

- Display exact values on hover.
- Show all three series in the tooltip.
- Include a readable legend.
- Avoid unnecessary chart gridlines.
- Maintain consistent colors throughout PROMETHEUS-X.

### Important Data Consistency Rule

The trend chart's `anomalies` field currently represents FAIL records only.

Do not label it simply as the overall Anomaly Rate.

Use `Failed Inspections` to distinguish it from the KPI, which includes both failed and review-required inspections.

### Empty State

`No inspection data yet.`

Supporting text:

`Run your first inspection to see activity trends here.`

---

## B. Severity Distribution

**Data source:**

`GET /api/v1/analytics/severity-distribution?days=30`

**Title:** Defect Severity Distribution

**Subtitle:** Severity classifications from inspection results.

### Chart Type

Donut chart.

### Categories

| Severity | Color |
|---|---|
| Critical | Red `#dc2626` |
| Major | Amber `#d97706` |
| Minor | Yellow `#ca8a04` |
| Informational | Gray `#6b7280` |

### Breakdown List

Display the following alongside the chart:

- Critical — count
- Major — count
- Minor — count
- Informational — count

### Interaction

- Hovering over a segment displays severity and count.
- Highlight the corresponding breakdown item.
- Clicking a severity category should navigate to matching inspection records if severity filtering is supported.

### Important Data Interpretation

Severity counts originate from the `severity_scores` table.

They represent severity classifications, not necessarily unique inspections.

Do not assume that the sum of severity counts equals the number of inspected products.

### Empty State

`No severity data available.`

Supporting text:

`Severity distribution will appear after inspections generate severity classifications.`

---

# 6. Recent Inspections

**Data source:**

`GET /api/v1/inspections?limit=20`

Display up to the eight most recent inspection records.

### Section Header

**Title:** Recent Inspections

**Action:** `View all →`

Navigate to `/history`.

### Table Columns

| Column | Data |
|---|---|
| ID | `INS-<id>` |
| Product | `product_serial` |
| Industry | Manufacturer / Scanner Unit industry |
| Status | Inspection decision |
| Severity | Severity classification |
| Score | `quality_score` |
| Date | Localized inspection date |

### Status Presentation

| Backend Decision | Display | Color |
|---|---|---|
| PASS | Completed | Green |
| REVIEW_REQUIRED | Needs Review | Amber |
| FAIL | Failed | Red |

### Severity Presentation

| Severity | Color |
|---|---|
| Critical | Red |
| Major | Orange |
| Minor | Yellow |
| Informational | Gray |

### Quality Score

Display as a numerical value between 0 and 100.

Do not invent a quality score when the backend returns null.

### Navigation

- Inspection ID opens `/inspections/<id>`.
- View All opens `/history`.
- Product information should remain readable without overflowing the table.

### Empty State

**Title:** No inspections yet.

**Description:** Submit your first test sample to populate your inspection history.

**Action:** `Go to Test Sample →`

Navigate to `/test-sample`.

---

# 7. Loading, Error & Data States

Every section must handle its own data state appropriately.

## Initial Loading

Display a structured skeleton layout resembling the final dashboard.

Avoid replacing the entire page with a blank screen.

## Refresh Loading

- Preserve previously loaded data.
- Display a small refresh indicator.
- Disable repeated refresh actions while requests are pending.

## API Failure

Display:

`Couldn't load dashboard data.`

Supporting text:

`Check that the backend is running on port 8000.`

Provide a Retry button.

Do not replace valid existing data with zeros when an API request fails.

## Partial Failure

If one analytics endpoint fails:

- Keep successfully loaded sections visible.
- Display an error state only in the affected section.
- Provide an appropriate retry mechanism.

## No Data

An empty database is not an application error.

Display meaningful empty states rather than error messages.

---

# 8. API Integration

The dashboard must use the existing backend endpoints.

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/analytics/summary?days=30` | KPI statistics |
| `GET /api/v1/analytics/trend?days=7` | Inspection trend |
| `GET /api/v1/analytics/severity-distribution?days=30` | Severity distribution |
| `GET /api/v1/inspections?limit=20` | Recent inspections |

### Request Behaviour

- Execute all four requests concurrently.
- Use the existing API client.
- Handle loading, success, empty and failure states.
- Avoid unnecessary API calls during component re-renders.
- Refresh all sections when the Refresh button is activated.

### Data Integrity

- Never calculate statistics from mock frontend data.
- Do not silently replace failed API responses with zero values.
- Use the backend as the source of truth.
- Ensure dates are handled consistently.
- Preserve the distinction between FAIL and REVIEW_REQUIRED.

---

# 9. Responsive Behaviour

### Desktop

- Four KPI cards in one row.
- Two analytics panels side by side.
- Recent inspections table spanning full width.

### Tablet

- Two KPI cards per row.
- Analytics panels stacked or resized according to available width.
- Table remains readable.

### Mobile

- KPI cards stacked or displayed in a compact two-column layout.
- Analytics panels stacked vertically.
- Table should support horizontal scrolling without breaking the page.
- Header actions must remain accessible.

---

# 10. Implementation Acceptance Criteria

The implementation is complete only when:

- [ ] All four KPI cards display actual backend values.
- [ ] KPI calculations match backend calculations.
- [ ] Inspection trend displays all three series correctly.
- [ ] Severity distribution uses actual severity records.
- [ ] Recent inspections display the latest eight records.
- [ ] Inspection IDs navigate to the correct detail pages.
- [ ] View All navigates to inspection history.
- [ ] Refresh re-fetches all four endpoints.
- [ ] Loading states are implemented.
- [ ] Empty states are implemented.
- [ ] API error states are implemented.
- [ ] Partial API failures do not destroy successfully loaded sections.
- [ ] No mock or hardcoded analytics data exists.
- [ ] Responsive layouts work correctly.
- [ ] Status and severity colors are consistent across PROMETHEUS-X.

---

# 11. Scope Restrictions

This implementation is strictly for the Overview page.

Do not:

- Modify backend analytics calculations.
- Introduce new database tables.
- Introduce mock inspection records.
- Add unnecessary analytics endpoints.
- Rebuild the inspection history page.
- Introduce unrelated dashboard widgets.
- Change existing API response contracts.

The goal is to improve the presentation, usability, and reliability of the existing dashboard without introducing unnecessary architectural complexity.

**Final Objective:** A clean, information-dense industrial inspection dashboard that communicates production quality, inspection activity, and outstanding issues immediately.