# 4G Network Performance Dashboard — Riyadh

**2 million crowdsourced signal measurements from real phones in Riyadh, turned into four interactive maps and charts that rank three mobile operators against each other.**

Which operator has the best coverage? Which one carries the most data, and where? Do certain handsets genuinely report worse signal? This project cleans two raw KPI datasets — **RSRP** (coverage, dBm) and **Traffic Volume** (data consumed, MB) — and builds an animated density time-lapse, an operator coverage map, an H3 hex-bin traffic hotspot map, and a device-vs-operator comparison, then reads the answers off them.

Short version of what the data says: the operator with the **weakest** coverage serves **more than half** the users, **10 hexagons out of 470** carry **60 %** of the city's downlink, and one handset brand is **89 %** of every sample — which changes how the rest of the charts should be read.

> **Data availability:** the datasets belong to **Ericsson** and are not mine to share, so `RSRP.csv` and `TrafficVolume.csv` are **not included** in this repository. The notebooks, cleaning logic, charts and findings are all here and fully documented; the outputs below were rendered from the real data.

Data visualization task for the Sultan Hussien Innovation Center AI challenge (Problem 1, §3.1).

---

## Contents

| File | What it does |
|---|---|
| `RSRP_EDA.ipynb` | Cleaning + EDA of `RSRP.csv` → `rsrp_clean.parquet` |
| `Traffic_Volume_EDA.ipynb` | Cleaning + EDA of `TrafficVolume.csv` → `traffic_clean.parquet` |
| `Dashboard.ipynb` | The 4 required charts + findings |
| `make_timelapse.py` | Renders Chart 1 to `timelapse.gif` |
| `make_screenshots.py` | Renders Charts 2–4 to `docs/*.png` |

Run order: `RSRP_EDA.ipynb` → `Traffic_Volume_EDA.ipynb` → `Dashboard.ipynb`.

## Setup

```bash
pip install pandas pyarrow plotly ipywidgets h3 kaleido pillow
```

The source CSVs are not distributed (see above). To run the notebooks end to end you need your own copy of `RSRP.csv` and `TrafficVolume.csv` in the project root, with the paths in the EDA notebooks updated to match.

---

## Data cleaning

**RSRP** (`RSRP.csv` → 1.98 M rows)

- Drop exact duplicates and the constant `Country` column
- Keep `RadioNetworkGeneration == 4G` and `RadioConnectionType == Mobile` — WiFi/Unknown says nothing about cellular coverage
- Keep RSRP within the valid **−140 … −40 dBm** range
- Parse `Timestamp` with `utc=True` (mixed offsets in the raw strings), then convert to `Asia/Riyadh` so `Hour` means *local* hour
- Lower-case `DeviceManufacturer` (`Lenovo` / `LENOVO` / `lenovo` were splitting into separate groups)
- De-duplicate on `Timestamp + lat + lon + operator + manufacturer` — the same physical sample is logged once per commercial `DeviceName`
- Add `RSRP_Quality` bands: Excellent ≥ −80, Good ≥ −90, Fair ≥ −100, Poor ≥ −110, Very Poor below

**Traffic Volume** (`TrafficVolume.csv` → 129.8 k rows)

- Same duplicate/`Country`/`Mobile`/timezone treatment
- **All radio generations kept** — 2G/3G is ~25 % of this file, and dropping it would understate every operator's real traffic
- `TrafficDirection` is part of the de-dup key, otherwise each `Uplink` row pairing a `Downlink` row is deleted
- Outliers kept — the bubble map sums traffic per area, and a genuinely huge session *is* the hotspot the chart should show

Both outputs are written to Parquet, which preserves dtypes and the timezone and reloads far faster than CSV.

**Coverage:** 2019-11-01 21:15 → 2019-11-04 23:59 local — a little over three days, not the full week the brief mentions.

---

## The dashboard

### 1. Hourly time-lapse of user density

Density map animated over local hour of day. The 2 M raw points are snapped to a ~110 m grid (3-decimal rounding) and counted per hour — ~5 k points per frame instead of 2 M. Colour range capped at the 99th percentile so a few very hot cells don't flatten every frame.

![Hourly user density time-lapse](docs/timelapse.gif)

### 2. Coverage map per operator

Mean RSRP per grid cell for the operator picked from a dropdown. Cells with fewer than 3 samples are dropped (a single reading is noise). The colour range is **hard-coded to −105 … −70 dBm**, not auto-scaled — otherwise every operator looks equally green and the dropdown compares nothing.

| Operator A | Operator C |
|---|---|
| ![Coverage map, Operator A](docs/chart2_coverage_a.png) | ![Coverage map, Operator C](docs/chart2_coverage_c.png) |

### 3. Downlink traffic hotspots per operator

Riyadh is cut into H3 hexagons, downlink traffic is summed per hexagon per operator, and each hexagon is drawn as a bubble sized by that total. The slider changes H3 resolution (6 ≈ 36 km², 9 ≈ 0.1 km²). Each operator is nudged a fraction of a hexagon radius off the shared centre so bubbles don't occlude each other — cosmetic only, the binning is untouched.

| Resolution 7 (~5 km² per hexagon) | Resolution 9 (~0.1 km² per hexagon) |
|---|---|
| ![Downlink hotspots at H3 resolution 7](docs/chart3_traffic_res7.png) | ![Downlink hotspots at H3 resolution 9](docs/chart3_traffic_res9.png) |

### 4. RSRP per device manufacturer per operator

Grouped bars, one group per manufacturer and one bar per operator. Dropdown picks the aggregation (Average / Minimum / Maximum / 90th percentile); slider sets the minimum samples a manufacturer needs on an operator to appear.

The y-axis range is derived from the selected metric, not hard-coded — a fixed window breaks `Minimum` (bottoms out at the −140 dBm cleaning floor) and `Maximum` (reaches −44 dBm). Manufacturers are sorted by the selected metric.

> The data has no user identifier, so *number of users* is approximated by **number of samples**.

| Average | 90th percentile |
|---|---|
| ![Average RSRP by manufacturer](docs/chart4_device_avg.png) | ![90th-percentile RSRP by manufacturer](docs/chart4_device_p90.png) |

> The dropdowns and sliders need a running kernel — open `Dashboard.ipynb` and run it. A static render of the `.ipynb` shows the last drawn figure only.

---

## Findings

**1. Coverage: C leads, A trails — and A carries the most users.**
Mean RSRP is **−80.9 dBm** for C against **−84.6** for B and **−85.5** for A. Only **4.5 %** of C's samples fall below −100 dBm, against **9.1 %** for B and **17.1 %** for A. The bottom decile separates them sharpest: C's P10 is **−96 dBm**, A's is **−107 dBm** — ~11 dB, more than a tenfold difference in received power. Yet **A accounts for 54.6 % of all RSRP samples**, more than B and C combined. The weakest coverage serves the largest population.

**2. Traffic: B moves the data, A moves the people.**
B carries **64.6 % of all downlink traffic from 28.7 % of samples**; A is the mirror image at **49.6 % of samples but 23.9 % of downlink GB**. Per sample, a B user pulls roughly **six times** the downlink of an A user. DL/UL ratios say the same: B **17.8:1**, A **10.9:1**, C **8.3:1** — a video/download-heavy mix on B, a more upload-balanced one on C. **B is a capacity story, A is a coverage story.**

**3. Downlink is extremely concentrated, and the hotspots are B's.**
At H3 resolution 7, **10 hexagons out of 470 carry 60.5 % of Riyadh's downlink** — ~50 km² of the city accounting for two thirds of the data. The largest hexagon holds **805 GB for B** against 0.9 GB for A and 0.1 GB for C. That ~900:1 ratio is too lopsided to be real demand; more likely one very heavy user or a small cluster — a caution against reading these bubbles as market share.

**4. The city breathes: a 6× day/night swing.**
Activity troughs at **04:00 (22.5 k samples)** and peaks at **16:00 (140.1 k)** — a **6.2×** swing, with a broad elevated block from **16:00–18:00** holding past 22:00. This is a Riyadh evening-social pattern, not the twin commuter spikes of a European city; the busy hour to plan against is the late afternoon, not the morning. Median RSRP runs 6–7 dB *better* in the dead hours, but that mixes network load with a change in who is measuring — don't over-read it.

**5. Handsets: the ranking is real, the tail is not.**
**Samsung is 89.1 % of every sample**; Huawei is second at 3.0 % and nothing else clears 1.5 %. Among the 13 manufacturers with ≥1,000 samples on an operator the spread is ~14 dB — weakest HMD Global (−89.9), Sony (−89.0), Lenovo (−88.5); strongest TCL (−75.9), Huawei (−80.2), Xiaomi (−83.2). The **HMD Global / Sony / Lenovo cluster sits 4–6 dB below Samsung**, a real and actionable gap for a care team. Two warnings, both demonstrable with the slider: **TCL's −75.9 is not a finding** (raise the threshold and it disappears), and **Samsung is the baseline, not a competitor** — at 89 % of the data its average *is* the network average.

---

## Notes and limitations

- Crowdsourced data — sample density reflects where the app's users are, not where the population is.
- No user identifier, so "users" is approximated by sample count throughout.
- ~3 days of data, not the full week stated in the brief.
