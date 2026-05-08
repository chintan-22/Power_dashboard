# Durable Electric Power Dashboard - Detailed Work Documentation

## 1. Project Overview

This project is a Streamlit dashboard for Durable Electric Power generation forecast analysis. The dashboard compares actual electricity generation against forecasted generation, calculates forecast accuracy metrics, identifies best and worst performers, checks data quality, and presents the results in a professional electric utility operations interface.

The project was built around a raw SQLite database named `assignment.db`, which contains two main tables:

- `actual_gen`
- `forecast_gen`

Both tables include the same core fields:

- `DATE_TIME`
- `MARKET_DATE`
- `DEVICE_ID`
- `GEN_MW`
- `GEN_MW_MAX`
- `STATUS`
- `FUEL_TYPE`
- `PLANT_NAME`

The key business meaning is:

- `actual_gen.GEN_MW` is the actual generation.
- `forecast_gen.GEN_MW` is the forecast generation.

The dashboard analyzes matched actual and forecast records only. Matching is performed with an `INNER JOIN` on:

- `DATE_TIME`
- `DEVICE_ID`

This means all forecast accuracy metrics are calculated only where both actual and forecast records exist.

## 2. AI Assistance Disclosure

OpenAI Codex and GPT were used during this project as development assistants. They helped with code generation, debugging, refactoring, performance optimization, documentation, deployment preparation, and explanation of the work completed.

The final implementation decisions, project direction, data definitions, and dashboard requirements were controlled by the project owner. Codex and GPT were used as productivity tools to accelerate development and improve code quality.

## 3. Main Project Goals

The project started as a working Streamlit dashboard and was improved into a more production-style analytics dashboard.

The main goals were:

1. Compare actual vs forecasted electricity generation.
2. Calculate forecast accuracy KPIs.
3. Identify best and worst performing devices, plants, and fuel types.
4. Provide plant and fuel analysis.
5. Add data quality reporting.
6. Improve filter speed and dashboard responsiveness.
7. Build a preprocessing pipeline so Streamlit does not repeatedly join raw database tables.
8. Add a professional electric power grid visual theme.
9. Make the GitHub repository deployable without committing the raw 863 MB SQLite database.
10. Prepare deployment support for Streamlit Cloud, Render, and limited Vercel compatibility.

## 4. Important Metric Definitions

The bias definition was kept consistent throughout the project:

```text
Bias = Actual - Forecast
```

Interpretation:

- Positive bias means underforecasting because actual generation is higher than forecast.
- Negative bias means overforecasting because forecast generation is higher than actual.

Other metrics used:

```text
ERROR_MW = ACTUAL_MW - FORECAST_MW
ABS_ERROR_MW = abs(ERROR_MW)
SQUARED_ERROR = ERROR_MW ** 2
MAE = average absolute error
RMSE = square root of average squared error
MAPE = average percentage error where actual generation is greater than zero
WAPE = total absolute error / total actual generation magnitude
Energy Accuracy = 100 - WAPE
```

MAPE is shown as supporting information only because generation data can contain zero or very small actual values, which makes MAPE unstable. Energy Accuracy based on WAPE was added because it is more stable for this kind of electricity generation data.

## 5. Current Repository Structure

The main files are located at the repository root:

- `app.py` - main Streamlit dashboard.
- `streamlit_app.py` - Streamlit Cloud entrypoint wrapper that runs `app.py`.
- `utils.py` - data loading, filtering, metric calculation, rankings, and insights.
- `charts.py` - reusable Plotly chart functions.
- `styles.py` - custom CSS, KPI cards, insight cards, section headers, and theme helpers.
- `preprocess.py` - production-style preprocessing pipeline.
- `data_exploration.py` - database exploration script.
- `data_cleaner.py` - supporting data cleaning utilities.
- `requirements.txt` - Python dependencies.
- `README.md` - user-facing documentation.
- `render.yaml` - Render deployment configuration.
- `vercel.json` - Vercel compatibility configuration.
- `.streamlit/config.toml` - Streamlit configuration.
- `.gitignore` - ignores local database and development artifacts.
- `data/` - preprocessed analytics files used by the dashboard.
- `assignment.db` - raw SQLite database, kept locally and ignored by Git.

## 6. Data Exploration Work

The initial work included exploring the raw SQLite database to understand:

- Table names.
- Table schemas.
- Row counts.
- Date ranges.
- Available device IDs.
- Plant names.
- Fuel types.
- Missing values.
- Negative generation values.
- Capacity violations.
- Matching behavior between actual and forecast records.

Important raw data facts identified:

- `actual_gen` row count: 1,995,177.
- `forecast_gen` row count: 1,990,148.
- The matched inner-join dataset contains about 1,978,813 records.
- January 2025 forecast data is not zero overall.
- January raw forecast total was checked and confirmed to be about 7,671,895.12 MW.

This exploration helped confirm that the dashboard should use an inner join and that missing metadata should be handled carefully without changing the raw database values.

## 7. SQLite Performance Improvements

The raw database was large enough that direct repeated queries from Streamlit became slow, especially when changing date filters.

SQLite indexes were added or supported for:

- `actual_gen(MARKET_DATE)`
- `forecast_gen(MARKET_DATE)`
- `actual_gen(DATE_TIME, DEVICE_ID)`
- `forecast_gen(DATE_TIME, DEVICE_ID)`
- `actual_gen(DEVICE_ID)`
- `forecast_gen(DEVICE_ID)`
- `actual_gen(PLANT_NAME)`
- `forecast_gen(PLANT_NAME)`
- `actual_gen(FUEL_TYPE)`
- `forecast_gen(FUEL_TYPE)`

These indexes improved direct database query performance, but the bigger improvement came from moving repeated join and aggregation work into a preprocessing pipeline.

## 8. Preprocessing Pipeline

The largest architecture improvement was the creation of `preprocess.py`.

The preprocessing architecture is:

```text
Raw assignment.db
        |
        v
preprocess.py
        |
        v
cleaned matched dataset
        |
        v
pre-aggregated Parquet analytics files
        |
        v
fast Streamlit dashboard
```

### 8.1 Pipeline Purpose

The purpose of the preprocessing pipeline is to perform expensive operations once instead of repeatedly during dashboard interaction.

Before preprocessing, the dashboard had to repeatedly:

- Query SQLite.
- Join `actual_gen` and `forecast_gen`.
- Clean columns.
- Calculate errors.
- Aggregate results.

After preprocessing, the dashboard reads ready-to-use Parquet files.

### 8.2 Pipeline Inputs

Input database:

```text
assignment.db
```

Required tables:

```text
actual_gen
forecast_gen
```

### 8.3 Join Logic

The pipeline uses an inner join only:

```sql
FROM actual_gen a
INNER JOIN forecast_gen f
    ON a.DATE_TIME = f.DATE_TIME
   AND a.DEVICE_ID = f.DEVICE_ID
```

The selected generation columns are:

```sql
a.GEN_MW AS ACTUAL_MW
f.GEN_MW AS FORECAST_MW
```

No left join or full outer join is used. Missing forecast rows are not filled as zero.

### 8.4 Metadata Handling

The pipeline uses `COALESCE` for plant and fuel metadata:

```sql
COALESCE(a.PLANT_NAME, f.PLANT_NAME, 'Unknown Plant') AS PLANT_NAME
COALESCE(a.FUEL_TYPE, f.FUEL_TYPE, 'Unknown Fuel') AS FUEL_TYPE
```

This keeps the raw database unchanged while giving the dashboard usable metadata labels.

### 8.5 Chunk Processing

The joined query is read in chunks using `pandas.read_sql_query`.

Default chunk size:

```text
100,000 rows
```

This avoids loading the full joined dataset into memory all at once during preprocessing.

### 8.6 Cleaned Fields

Each chunk is cleaned by:

- Parsing `DATE_TIME`.
- Parsing `MARKET_DATE`.
- Filling missing `PLANT_NAME` with `Unknown Plant`.
- Filling missing `FUEL_TYPE` with `Unknown Fuel`.
- Converting generation columns to numeric.
- Preserving original status columns.

### 8.7 Calculated Fields

The preprocessing pipeline creates:

- `ERROR_MW`
- `ABS_ERROR_MW`
- `SQUARED_ERROR`
- `APE`
- `CAPACITY_UTILIZATION`
- `DAY`
- `WEEK`
- `MONTH`

The month field is created using month-start timestamps so monthly grouping is consistent.

### 8.8 Output Files

The pipeline creates the following dashboard-ready files:

- `data/matched_generation.parquet`
- `data/daily_summary.parquet`
- `data/weekly_summary.parquet`
- `data/monthly_summary.parquet`
- `data/plant_summary.parquet`
- `data/device_summary.parquet`
- `data/fuel_summary.parquet`
- `data/data_quality_summary.csv`
- `data/preprocess_metadata.json`

### 8.9 Summary Files

The summary files include metrics such as:

- `total_actual_mw`
- `total_forecast_mw`
- `forecast_difference_mw`
- `mae`
- `rmse`
- `bias`
- `mape`
- `wape`
- `energy_accuracy_pct`
- `avg_capacity_utilization`
- `observation_count`
- `unique_devices`
- `unique_plants`

The groupings are:

- Daily summary grouped by `DAY` and `FUEL_TYPE`.
- Weekly summary grouped by `WEEK` and `FUEL_TYPE`.
- Monthly summary grouped by `MONTH` and `FUEL_TYPE`.
- Plant summary grouped by `PLANT_NAME` and `FUEL_TYPE`.
- Device summary grouped by `DEVICE_ID`, `PLANT_NAME`, and `FUEL_TYPE`.
- Fuel summary grouped by `FUEL_TYPE`.

### 8.10 Data Quality Summary

The preprocessing pipeline also produces data quality metrics:

- Actual row count.
- Forecast row count.
- Matched row count.
- Actual-only count.
- Forecast-only count.
- Duplicate actual records by `DATE_TIME + DEVICE_ID`.
- Duplicate forecast records by `DATE_TIME + DEVICE_ID`.
- Missing plant counts.
- Missing fuel counts.
- Missing generation counts.
- Negative generation counts.
- Generation greater than capacity counts.
- Zero or missing capacity counts.
- Actual status distribution.
- Forecast status distribution.

### 8.11 Metadata File

The metadata file includes:

- Preprocessing timestamp.
- Source database path.
- Source database file size.
- Matched row count.
- Output file names.
- Date min and max.
- Unique device count.
- Unique plant count.
- Fuel type count.
- Chunk size.
- Pipeline version.

### 8.12 Validation Added

The preprocessing pipeline includes validation checks:

- Database table existence.
- SQLite integrity check.
- January forecast validation.
- Monthly summary consistency.
- Daily summary consistency.
- Plant summary consistency.
- Device summary consistency.

January validation was added because a dashboard view appeared to show forecast zero for small ranking rows. The validation confirmed that January forecast totals are not zero overall and helped separate preprocessing correctness from ranking interpretation.

## 9. Streamlit Dashboard Pipeline

The dashboard pipeline in `app.py` now works like this:

```text
Start Streamlit app
        |
        v
Check required preprocessed files
        |
        v
Load Parquet analytics layer with st.cache_data
        |
        v
Render sidebar filters inside Apply Filters form
        |
        v
Filter matched dataset
        |
        v
Calculate KPIs, rankings, insights
        |
        v
Render charts, tables, downloads, and data quality views
```

The dashboard checks that required analytics files exist. If they are missing, it shows a clear instruction:

```bash
python preprocess.py --force
```

This prevents unclear errors when the Parquet layer is not available.

## 10. Filtering Pipeline

The sidebar filters were placed inside a Streamlit form so the dashboard does not reload every time a widget changes.

The user changes filters and then clicks:

```text
Apply Filters
```

Filters include:

- Market date range.
- Plant name.
- Device ID.
- Fuel type.
- Exclude unknown plant/fuel.
- Minimum absolute error threshold.
- Trend frequency.
- Ranking level.
- Ranking metric.
- Top N slider.

This improved dashboard usability and performance because multiple filter changes can be applied together.

## 11. Analytics Layer Loading

The dashboard uses `utils.load_analytics_layer(data_dir)` to load:

- Matched dataset.
- Daily summary.
- Weekly summary.
- Monthly summary.
- Plant summary.
- Device summary.
- Fuel summary.
- Data quality summary.
- Metadata.

The function uses Streamlit caching so repeated interactions do not reload the files unnecessarily.

## 12. Metric Calculation Pipeline

The main KPI calculation happens in:

```text
utils.calculate_metrics_from_filtered_data()
```

It calculates:

- Total actual generation.
- Total forecast generation.
- Forecast difference.
- MAE.
- RMSE.
- Bias.
- MAPE.
- WAPE.
- Energy Accuracy.
- Average capacity utilization.
- Observation count.
- Unique devices.
- Unique plants.
- Fuel type count.

Energy Accuracy was changed to use WAPE rather than MAPE because WAPE is more stable for electricity generation records with zero or near-zero actual generation.

## 13. Ranking Pipeline

The ranking pipeline supports:

- Device ranking.
- Plant ranking.
- Fuel type ranking.

Ranking metrics:

- MAE.
- RMSE.
- MAPE.
- Bias.

Rules:

- For MAE, RMSE, and MAPE, best means lowest error and worst means highest error.
- For Bias, best means closest to zero and worst means largest absolute bias.

An issue was identified where inactive or very low-activity records could appear as top performers because their MAE was zero or close to zero. Ranking support columns were added to distinguish active groups from inactive groups.

The ranking pipeline now uses activity checks so zero-activity groups do not incorrectly dominate the best performer table.

## 14. Charting Pipeline

The charting layer was moved into `charts.py`.

Reusable chart functions include:

- `actual_vs_forecast_line`
- `error_histogram`
- `actual_vs_forecast_scatter`
- `error_by_fuel_bar`
- `ranking_bar_chart`
- `capacity_utilization_bar`
- `utilization_vs_error_scatter`

The charts use Plotly and a shared dark utility-control theme.

The actual generation line is electric blue. The forecast line is cyan and dashed. Error and risk views use amber, red, and green severity colors.

One important bug was fixed in the utilization vs error scatter plot. Plotly marker sizes cannot be negative, so marker size now uses absolute generation magnitude instead of raw signed generation totals.

## 15. Automatic Insights Pipeline

Automatic insights were added near the top of the dashboard.

Insights include:

1. Overall forecast tendency.
2. Fuel type with highest MAE.
3. Plant with highest MAE.
4. Device with highest MAE.
5. Best-performing device.
6. Large-miss signal comparing RMSE and MAE.
7. Percent difference between total actual and total forecast.
8. Capacity utilization insight.

The insights are shown as business-friendly operational cards.

## 16. KPI Card Improvements

The KPI cards were upgraded to use custom HTML and CSS through `styles.py`.

KPI cards show:

- Total Actual.
- Total Forecast.
- MAE.
- RMSE.
- Bias.
- Energy Accuracy.

Each KPI card has a hover tooltip explaining:

- What the metric means.
- How it is calculated.
- How to interpret it.

Special characters in tooltip text are escaped safely so the HTML layout does not break.

The KPI cards also include severity styling:

- Green for stable or good values.
- Amber for caution.
- Red for high-risk values.
- Neutral blue for informational values.

## 17. Visual Theme Upgrade

The dashboard was visually upgraded into a modern electric grid control-room style.

The theme includes:

- Dark navy and near-black background.
- Subtle grid-line background pattern.
- Electric blue generation accents.
- Cyan highlights.
- Amber warning colors.
- Green success colors.
- Red danger colors.
- Dark panels and cards.
- Custom KPI cards.
- Operational insight cards.
- Themed sidebar control panel.
- Themed Plotly charts.
- Themed data quality alert cards.

The header was updated to:

```text
DURABLE ELECTRIC POWER
Generator Forecast Performance Command Center | 2025
```

The theme is implemented mainly in:

- `styles.py`
- `charts.py`
- `app.py`

The data logic was not changed during the visual theme upgrade.

## 18. Dashboard Tabs

The dashboard contains these main tabs:

### Overview

Shows high-level actual vs forecast trends, generation by fuel type, and top plants.

### Forecast Accuracy

Shows error metrics, rankings, scatter plots, and error distributions.

### Top and Worst Performers

Shows best and worst rankings by device, plant, or fuel type.

### Plant and Fuel Analysis

Shows utilization and fuel mix views.

### Data Quality

Shows preprocessing quality metrics, status distributions, and metadata.

### Drilldowns and Downloads

Shows filtered matched records and allows CSV download of filtered results.

## 19. Data Quality and Edge Case Handling

Several edge cases were handled:

- Empty filter results show a clean warning instead of crashing.
- Missing preprocessed files show a clear command to run preprocessing.
- Unknown plant and fuel values are labeled clearly.
- Zero actual generation is handled carefully in percentage metrics.
- MAPE excludes rows where actual generation is zero.
- WAPE is used for Energy Accuracy.
- Negative generation values are retained and flagged rather than silently removed.
- Generation above capacity is flagged in data quality reporting.

## 20. Deployment and GitHub Work

The raw `assignment.db` file is about 863 MB, which is larger than GitHub's 100 MB file limit. A push initially failed because the database was included in Git history.

To fix this:

- `assignment.db` was removed from Git tracking.
- The file was kept locally.
- `.gitignore` was updated so database files are ignored.
- The commit history was amended so GitHub no longer received the large database file.

The preprocessed Parquet analytics files were included because the deployed dashboard needs them and the largest file is under GitHub's hard 100 MB file limit.

Deployment support files added:

- `render.yaml`
- `vercel.json`
- `.streamlit/config.toml`
- `streamlit_app.py`

### Streamlit Cloud

Streamlit Cloud expected:

```text
streamlit_app.py
```

The project originally used:

```text
app.py
```

To solve this without changing the working local app, a small wrapper file was added:

```text
streamlit_app.py
```

It runs `app.py` and keeps the local command unchanged:

```bash
streamlit run app.py
```

### Render

Render deployment was supported with:

```yaml
startCommand: "streamlit run app.py --server.port $PORT --server.address 0.0.0.0"
```

### Vercel

A `vercel.json` file was added for compatibility, but Vercel is not the recommended deployment target because Streamlit runs a persistent web server and Vercel is designed for static and serverless applications.

Recommended deployment targets:

- Streamlit Community Cloud.
- Render.

## 21. Requirements

The required packages are:

- `streamlit`
- `pandas`
- `numpy`
- `plotly`
- `pyarrow`

These are listed in `requirements.txt`.

## 22. Commands Used

Install dependencies:

```bash
pip install -r requirements.txt
```

Run preprocessing:

```bash
python preprocess.py --db assignment.db --out data --chunksize 100000 --force
```

Run the dashboard locally:

```bash
streamlit run app.py
```

Run the dashboard on a specific port:

```bash
streamlit run app.py --server.port 8502
```

Render start command:

```bash
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

Streamlit Cloud main file path:

```text
streamlit_app.py
```

## 23. Validation Performed

Validation included:

- Confirming the app runs locally with Streamlit.
- Confirming the dashboard responds on `localhost:8502`.
- Checking Python syntax with `py_compile`.
- Checking charts with a chart smoke test.
- Verifying January forecast totals were not zero after preprocessing.
- Verifying summary files match matched dataset totals.
- Verifying `assignment.db` is not tracked by Git.
- Verifying `data/` files are available for hosted dashboard loading.
- Verifying Streamlit Cloud has a valid `streamlit_app.py` entrypoint.

## 24. Main Files Created or Improved

Created:

- `preprocess.py`
- `charts.py`
- `styles.py`
- `streamlit_app.py`
- `render.yaml`
- `vercel.json`
- `.streamlit/config.toml`
- `DETAILED_WORK_DOCUMENTATION.md`

Improved:

- `app.py`
- `utils.py`
- `README.md`
- `.gitignore`
- Documentation files such as performance and speed guides.

Generated:

- `data/matched_generation.parquet`
- `data/daily_summary.parquet`
- `data/weekly_summary.parquet`
- `data/monthly_summary.parquet`
- `data/plant_summary.parquet`
- `data/device_summary.parquet`
- `data/fuel_summary.parquet`
- `data/data_quality_summary.csv`
- `data/preprocess_metadata.json`

## 25. Final System Summary

The final project is a Streamlit-based electric power operations dashboard that uses a preprocessed Parquet analytics layer for speed.

The dashboard:

- Uses matched actual and forecast records only.
- Preserves the bias definition as `Actual - Forecast`.
- Uses WAPE-based Energy Accuracy for stable generation accuracy reporting.
- Provides KPIs, rankings, insights, charts, data quality checks, and drilldowns.
- Uses an electric power grid visual theme.
- Avoids repeated expensive SQLite joins during interaction.
- Is prepared for Streamlit Cloud and Render deployment.
- Keeps the raw database local and out of GitHub.

Codex and GPT were used as AI development assistants throughout the implementation, debugging, optimization, documentation, and deployment preparation process.
