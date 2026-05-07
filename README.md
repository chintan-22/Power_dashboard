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
├── app.py                 # Main Streamlit dashboard application
├── utils.py              # Utility functions for data processing
├── data_exploration.py   # Database exploration and statistics script
├── requirements.txt      # Python dependencies
├── README.md            # This file
└── assignment.db        # SQLite database (should be in parent directory)
```

## Installation

### Prerequisites
- Python 3.8 or higher
- SQLite database file (`assignment.db`) placed in the parent directory of this project

### Step 1: Clone or Download Project

```bash
cd durable_power_dashboard
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

```bash
python preprocess.py --db assignment.db --out data --chunksize 100000 --force
```

### Start the Dashboard

```bash
streamlit run app.py
```

The dashboard will open in your default browser at `http://localhost:8501`

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

### Mean Absolute Error (MAE)
- **Formula:** Average of |Actual - Forecast|
- **Interpretation:** Lower is better. Represents average magnitude of prediction error.
- **Use:** Quick measure of forecast accuracy without penalizing large errors as much as RMSE.

### Root Mean Squared Error (RMSE)
- **Formula:** √(Average of (Actual - Forecast)²)
- **Interpretation:** Lower is better. Penalizes larger errors more heavily.
- **Use:** When large errors are particularly costly.

### Bias
- **Formula:** Average of (Actual - Forecast)
- **Interpretation:** 
  - **Positive bias:** Underforecasting (actual > forecast on average)
  - **Negative bias:** Overforecasting (forecast > actual on average)
  - **Zero bias:** On average, forecast matches actual
- **Use:** Understand systematic forecast tendency.

### Mean Absolute Percentage Error (MAPE)
- **Formula:** Average of |Actual - Forecast| / |Actual| × 100
- **Interpretation:** Error as percentage of actual value.
- **Note:** Only calculated for non-zero actual values to avoid division errors.
- **Use:** Normalize errors across different generation scales.

## Data Quality Assumptions & Decisions

### Missing Value Handling
1. **PLANT_NAME/FUEL_TYPE:** Filled with 'Unknown Plant' / 'Unknown Fuel' for analysis
2. **GEN_MW (Generation):** Missing values filled with 0 (conservative assumption)
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
- Dashboard updates in real-time as filters change
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
