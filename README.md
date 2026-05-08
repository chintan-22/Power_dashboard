# Durable Electric Power - Generation Forecast Dashboard

A comprehensive, interactive Streamlit dashboard for analyzing actual vs. forecasted electricity generation data from Durable Electric Power, LLC.

## Overview

This dashboard compares actual generation performance against forecasts, calculates accuracy metrics, identifies top and worst-performing generators/plants, and provides comprehensive data quality insights.

The dashboard uses a custom electric power grid theme with dark utility-control styling, electric blue generation accents, and severity-based alert colors.

**Key Features:**
- 📊 Real-time comparison of actual vs. forecast generation
- 📈 Forecast accuracy metrics (MAE, RMSE, MAPE, Bias)
- 🏆 Identification of top and worst performers
- 🏭 Plant and fuel type analysis with capacity utilization
- ⚠️ Comprehensive data quality reporting
- 🎛️ Interactive filters by date, plant, device, and fuel type
- 📊 Responsive charts and data visualizations

## Project Structure

```
durable_power_dashboard/
├── app.py                         # Main Streamlit dashboard application
├── streamlit_app.py               # Streamlit Cloud entrypoint wrapper
├── utils.py                       # Data loading, filtering, metrics, rankings
├── charts.py                      # Reusable Plotly chart builders
├── styles.py                      # Custom dashboard theme and card helpers
├── preprocess.py                  # SQL-to-Parquet preprocessing pipeline
├── data_exploration.py            # Database exploration and statistics script
├── data_cleaner.py                # Supporting data quality utilities
├── data/                          # Preprocessed Parquet analytics layer
├── requirements.txt               # Python dependencies
├── render.yaml                    # Render deployment configuration
├── vercel.json                    # Vercel compatibility configuration
├── README.md                      # This file
└── assignment.db                  # Local raw SQLite database, ignored by Git
```

## Installation

### Prerequisites
- Python 3.8 or higher
- Python packages from `requirements.txt`
- The included `data/` folder for normal dashboard use
- Optional: local SQLite database file (`assignment.db`) in the project root if you want to rebuild the analytics layer

### Step 1: Clone or Download Project

```bash
git clone https://github.com/chintan-22/Power_dashboard.git
cd Power_dashboard
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Using venv
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Or using conda
conda create -n durable-power python=3.10
conda activate durable-power
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## Running the Dashboard

### Build the Analytics Layer

The repository includes preprocessed Parquet files in `data/`, so the dashboard can run immediately after installing dependencies. Rebuild the analytics layer only when `assignment.db` is available locally or when the raw data changes.

```bash
python preprocess.py --db assignment.db --out data --chunksize 100000 --force
```

### Start the Dashboard

```bash
streamlit run app.py
```

The dashboard will open in your default browser at `http://localhost:8501`

## Design Choices Summary

- **Matched-record analysis:** Actual and forecast records are matched with a SQL `INNER JOIN` on `DATE_TIME` and `DEVICE_ID`; unmatched records are reported in the Data Quality tab but are not used for accuracy metrics.
- **Preprocessed analytics layer:** SQL is used to extract, validate, and join raw SQLite data once. Streamlit reads Parquet files afterward for faster filtering and charting.
- **Bias definition:** `Bias = Actual - Forecast`. Positive bias means underforecasting; negative bias means overforecasting.
- **Metric choice:** MAE and RMSE are shown in MW because dispatch decisions are operationally MW-based. MAPE is supporting-only due to zero and near-zero generation rows. Energy Accuracy uses WAPE for a more stable percentage-style KPI.
- **AI disclosure:** OpenAI Codex and GPT were used as development assistants for implementation, debugging, documentation, and deployment preparation. The project owner should be prepared to explain each module and design decision.

### Explore the Database

To analyze the database structure and content:

```bash
python data_exploration.py
```

This will print comprehensive statistics about the database including:
- Table schemas
- Row counts
- Date ranges
- Unique values
- Missing data
- Data quality issues

## Database Structure

### actual_gen Table
| Column | Type | Description |
|--------|------|-------------|
| DATE_TIME | TEXT | Timestamp in America/Chicago timezone |
| MARKET_DATE | DATE | Trading date |
| DEVICE_ID | TEXT | Unique generator identifier |
| GEN_MW | FLOAT | Actual generation dispatch |
| GEN_MW_MAX | FLOAT | Maximum power capacity |
| STATUS | BIGINT | Generator status |
| FUEL_TYPE | TEXT | Type of fuel (coal, gas, wind, etc.) |
| PLANT_NAME | TEXT | Name of generating plant |

### forecast_gen Table
Same structure as `actual_gen` but containing forecasted values.

## Dashboard Tabs

### 1. Overview
**Purpose:** High-level summary of generation performance

**Contents:**
- KPI cards: Total Actual, Total Forecast, MAE, RMSE, Bias
- Time series chart showing actual vs. forecast trends
- Bar charts of generation by fuel type and plant (top 10)

**Use Case:** Quick check of overall forecast accuracy and generation patterns

### 2. Forecast Accuracy
**Purpose:** Detailed accuracy analysis by fuel type and plant

**Contents:**
- Error metrics (MAE, RMSE, Bias, MAPE) by fuel type and plant
- Scatter plot of actual vs. forecast (with perfect forecast reference line)
- Error distribution histograms
- Explanation of bias interpretation

**Use Case:** Identify which fuel types or plants need forecast improvement

### 3. Top & Worst Performers
**Purpose:** Rank generators/plants by forecast accuracy

**Contents:**
- Top 10 best performers (lowest MAE)
- Top 10 worst performers (highest MAE)
- Aggregation level selector: Device, Plant, or Fuel Type
- Summary statistics

**Use Case:** Focus improvement efforts on worst-performing assets

### 4. Plant & Fuel Analysis
**Purpose:** Operational efficiency and utilization patterns

**Contents:**
- Capacity utilization by plant and fuel type
- Monthly trends of actual vs. forecast
- Fuel mix pie chart
- Plant and fuel type summary statistics

**Use Case:** Understand generation patterns and capacity constraints

### 5. Data Quality
**Purpose:** Identify data issues that may affect analysis

**Contents:**
- Missing value counts
- Record matching status (actual-only, forecast-only)
- Negative value detection
- Capacity violation detection
- Status distributions
- Duplicate record counts

**Use Case:** Validate data before making strategic decisions

## Error Metrics Explained

### Dataset Context For Metric Choices

The matched analytics layer contains 1,978,813 actual/forecast records across 300 devices. This dataset has many low-output periods: 5.35% of matched rows have exactly zero actual generation, 48.05% have exactly zero forecast generation, and more than half of the rows are near zero by absolute MW. Actual generation ranges from about -9.21 MW to 865.64 MW, while forecast generation ranges from about -1.24 MW to 835.00 MW. Because the fleet contains both very small and very large generation values, the dashboard uses MW-based metrics for operational ranking and WAPE-based Energy Accuracy for a more stable percentage-style KPI.

### Mean Absolute Error (MAE)
- **Formula:** Average of |Actual - Forecast|
- **Interpretation:** Lower is better. Represents average magnitude of prediction error.
- **Dataset-specific use:** MAE is the primary ranking metric because it stays in MW, which is easy to interpret for dispatch and operations teams. Since the dataset contains generators with a wide MW range, MAE makes it clear which devices, plants, or fuel classes are missing forecasts by meaningful energy amounts.

### Root Mean Squared Error (RMSE)
- **Formula:** √(Average of (Actual - Forecast)²)
- **Interpretation:** Lower is better. Penalizes larger errors more heavily.
- **Dataset-specific use:** RMSE is useful because the data includes occasional large misses, with absolute errors reaching more than 800 MW. When RMSE is much higher than MAE, it signals that the forecast is usually reasonable but sometimes misses badly, which matters for reliability planning and dispatch risk.

### Bias
- **Formula:** Average of (Actual - Forecast)
- **Interpretation:** 
  - **Positive bias:** Underforecasting (actual > forecast on average)
  - **Negative bias:** Overforecasting (forecast > actual on average)
  - **Zero bias:** On average, forecast matches actual
- **Dataset-specific use:** Bias matters for power dispatch because direction is as important as size. Persistent underforecasting can leave operators short of expected generation, while persistent overforecasting can make planned supply look stronger than reality. In this dataset, the overall matched-record bias is negative, which indicates a tendency toward overforecasting in the selected full dataset.

### Mean Absolute Percentage Error (MAPE)
- **Formula:** Average of |Actual - Forecast| / |Actual| × 100
- **Interpretation:** Error as percentage of actual value.
- **Note:** Only calculated for non-zero actual values to avoid division errors.
- **Dataset-specific use:** MAPE is treated as supporting information rather than the main KPI because more than half of the matched records are near zero by absolute actual MW. Percentage errors can become unstable or misleading when actual generation is zero or very small.

### Weighted Absolute Percentage Error (WAPE) and Energy Accuracy
- **Formula:** WAPE = SUM(|Actual - Forecast|) / SUM(|Actual|)
- **Energy Accuracy:** 100 - WAPE
- **Dataset-specific use:** WAPE is more stable than MAPE for this generation dataset because it compares total absolute error against total generation magnitude. This avoids letting many near-zero records dominate the dashboard's main percentage-style accuracy KPI.

## Data Quality Assumptions & Decisions

### Missing Value Handling
1. **PLANT_NAME/FUEL_TYPE:** Filled with 'Unknown Plant' / 'Unknown Fuel' for analysis
2. **GEN_MW (Generation):** Raw generation values are preserved in the preprocessing layer and missing generation counts are reported in data quality outputs
3. **Analysis:** All analysis performed on matched records (where both actual and forecast exist)

### Data Matching
- Records are matched using: `DATE_TIME AND DEVICE_ID`
- Only fully matched records are included in accuracy calculations
- Unmatched records are flagged in the Data Quality tab

### Zero Generation Handling
- Zero generation values are treated as valid (no removal)
- MAPE calculation skips records where actual generation is zero to avoid division errors
- Capacity utilization shows NaN for devices with zero capacity

### Negative Values
- Negative generation values are retained in analysis (may indicate grid anomalies)
- Flagged in Data Quality tab as potential issues
- Can be filtered out manually if needed for specific analysis

### Capacity Violations
- Cases where generation exceeds maximum capacity are flagged
- May indicate:
  - Data entry errors
  - Temporary overload conditions
  - Capacity rating updates during period
- Investigated in Data Quality tab

### Status Field
- Treated as categorical variable
- Status distributions analyzed in Data Quality tab
- Not used in accuracy calculations (assumes all records are valid observations)

## Filtering & Aggregation

### Sidebar Filters
1. **Date Range:** Select market date range (calendar picker)
2. **Plant Name:** Multiselect for one or more plants
3. **Device ID:** Multiselect for specific generators
4. **Fuel Type:** Multiselect for fuel categories
5. **Aggregation Level:** Choose how metrics are grouped:
   - **Device:** Individual generator performance
   - **Plant:** Plant-level aggregation
   - **Fuel Type:** Fuel category performance

### Filter Logic
- All filters use **AND** logic
- Leave filter empty to include all values
- Dashboard updates after clicking **Apply Filters**, which prevents unnecessary reloads while several filters are being changed
- Filtered results show in sidebar and all tabs

## Performance Notes

- Database queries are cached for 1 hour (adjustable in code)
- Large datasets may take time to load on first run
- For best performance, filter to specific date ranges or plants
- Sample data (5000 records) used for scatter plots to prevent lag

## Technical Stack

- **Frontend:** Streamlit 1.28+
- **Data Processing:** Pandas 2.0+, NumPy 1.24+
- **Visualization:** Plotly 5.17+
- **Database:** SQLite3
- **Language:** Python 3.8+

## Customization

### Adjust Cache TTL
In `utils.py`, modify the `ttl` parameter (in seconds):
```python
@st.cache_data(ttl=7200)  # Change from 3600 to 7200 for 2-hour cache
```

### Modify Chart Styling
Edit Plotly chart templates in `app.py`:
```python
template='plotly_white'  # Try: plotly_dark, ggplot2, seaborn, etc.
```

### Add New Filters
1. Add filter in sidebar (app.py)
2. Add WHERE clause to SQL query in `load_and_process_data()` (utils.py)

### Change Date Range Format
Modify the `get_date_range()` function in `utils.py` to adjust how dates are retrieved.

## Troubleshooting

### "Database not found" Error
**Solution:** Ensure `assignment.db` is in the parent directory of the project:
```
/path/to/parent/assignment.db
/path/to/parent/durable_power_dashboard/app.py
```

### Slow Dashboard Loading
**Solution:** 
- Filter to smaller date ranges
- Use plant/device filters to reduce data volume
- Clear cache: Streamlit menu → "Clear cache"

### Missing Data in Charts
**Solution:**
- Check Data Quality tab for unmatched records
- Verify date ranges don't exclude relevant data
- Ensure generation values aren't all zero for selected filters

### Import Errors
**Solution:**
```bash
pip install -r requirements.txt --upgrade
```

## Future Enhancements

- Forecast comparison across multiple models
- Seasonal decomposition analysis
- ML-based anomaly detection
- Export reports to PDF
- Scheduled automated reports
- Real-time data ingestion

## Preprocessing Pipeline and Analytics Layer

The dashboard now uses a production-style preprocessing step so Streamlit does not repeatedly join and clean the raw SQLite tables during interaction.

### SQL Querying Design Choice

The assignment requirement to query the data with SQL is met inside `preprocess.py`. The pipeline connects to `assignment.db`, checks the SQLite tables, creates indexes, and runs a SQL `INNER JOIN` query on `DATE_TIME` and `DEVICE_ID` to create the matched actual/forecast dataset. The Streamlit dashboard then reads the resulting Parquet files so interactive filtering stays fast.

This design intentionally separates SQL extraction from dashboard interaction:

- SQL is used for the raw data join, validation checks, row counts, duplicate checks, and data quality queries.
- Parquet is used after preprocessing because it is faster for repeated dashboard reads.
- The dashboard still analyzes only records produced by the SQL inner join.

The core SQL join is:

```sql
SELECT
    a.DATE_TIME,
    a.MARKET_DATE,
    a.DEVICE_ID,
    COALESCE(a.PLANT_NAME, f.PLANT_NAME, 'Unknown Plant') AS PLANT_NAME,
    COALESCE(a.FUEL_TYPE, f.FUEL_TYPE, 'Unknown Fuel') AS FUEL_TYPE,
    a.GEN_MW AS ACTUAL_MW,
    f.GEN_MW AS FORECAST_MW
FROM actual_gen a
INNER JOIN forecast_gen f
    ON a.DATE_TIME = f.DATE_TIME
   AND a.DEVICE_ID = f.DEVICE_ID;
```

### Why This Was Added

The raw database has nearly 4 million actual/forecast records. Joining those tables repeatedly in Streamlit made date-range filtering slower than necessary. The preprocessing pipeline performs the expensive work once, then writes dashboard-ready Parquet files.

### How To Run The Pipeline

```bash
cd /Users/chintanshah/Documents/Durable_Task/durable_power_dashboard
python preprocess.py --db assignment.db --out data --chunksize 100000 --force
```

### How To Run The Dashboard

```bash
streamlit run app.py
```

The dashboard expects the `data/` folder to exist. If files are missing, it will show a clear instruction to run `python preprocess.py --force`.

### Deployment Note

This is a Streamlit application, so deploy it on Streamlit Community Cloud, Render, Railway, or another host that can run a long-lived Python web process. Vercel is designed for static and serverless web apps and is not a good fit for this Streamlit dashboard.

For Streamlit Community Cloud:
- Repository: `chintan-22/Power_dashboard`
- Branch: `main`
- Main file path: `app.py`
- Python dependencies: `requirements.txt`

The raw `assignment.db` file is intentionally ignored because it is too large for GitHub. The preprocessed `data/` analytics files are included so the hosted dashboard can load without the raw database.

### Files Created

- `data/matched_generation.parquet`
- `data/daily_summary.parquet`
- `data/weekly_summary.parquet`
- `data/monthly_summary.parquet`
- `data/plant_summary.parquet`
- `data/device_summary.parquet`
- `data/fuel_summary.parquet`
- `data/data_quality_summary.csv`
- `data/preprocess_metadata.json`

### Important Definitions

- The preprocessing pipeline uses an `INNER JOIN` on `DATE_TIME` and `DEVICE_ID`.
- The dashboard analyzes only matched actual/forecast records.
- `Bias = Actual - Forecast`.
- Positive bias means underforecasting.
- Negative bias means overforecasting.

### Why Parquet Is Used

Parquet is columnar, compressed, and much faster for dashboard reads than repeatedly querying and joining SQLite tables. This improves filter speed and dashboard responsiveness while preserving the matched-record analysis rules.

## Contact & Support

For questions or issues with this dashboard, contact:
- **Organization:** Durable Electric Power, LLC
- **Date Created:** May 5, 2026

## License

Internal use only - Durable Electric Power, LLC

---

**Dashboard Version:** 1.0  
**Last Updated:** May 5, 2026
# Power_dashboard

## Deployment Notes

Local run:

```bash
streamlit run app.py
```

Preprocessing:

```bash
python preprocess.py --force
```

Recommended deployment:

- Streamlit Community Cloud
- Render

Render start command:

```bash
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

Vercel note:

Vercel may detect Python entrypoints, but Streamlit is not a standard Vercel Python serverless app. Streamlit runs a persistent web server, while Vercel expects serverless Python/ASGI/WSGI style apps. If Vercel fails, deploy on Streamlit Community Cloud or Render.
