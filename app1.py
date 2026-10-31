import pandas as pd
import streamlit as st


# ---------- PAGE SETTINGS ----------
st.set_page_config(
    page_title="Walmart Sales Dashboard",
    page_icon="🛒",
    layout="wide"
)


# ---------- DESIGN ----------
st.markdown(
    """
    <style>
    .walmart-header {
        background: #0053A0;
        padding: 24px 28px;
        border-radius: 14px;
        margin-bottom: 24px;
    }

    .walmart-header h1 {
        color: white;
        margin: 0;
        padding: 0;
    }

    .walmart-header p {
        color: #E6F1FF;
        margin: 10px 0 0;
    }

    [data-testid="stMetric"] {
        background-color: #EFF6FF;
        border: 1px solid #BFDBFE;
        border-left: 5px solid #0053A0;
        border-radius: 12px;
        padding: 18px;
    }

    [data-testid="stMetricLabel"],
    [data-testid="stMetricValue"] {
        color: #123458;
    }

    [data-testid="stMetricValue"] {
        font-size: 28px;
    }
    </style>

    <div class="walmart-header">
        <h1>🛒 Walmart Sales Dashboard</h1>
        <p>
            Explore weekly sales, store performance and holiday trends
        </p>
    </div>
    """,
    unsafe_allow_html=True
)


# ---------- UPLOAD DATA ----------
uploaded_file = st.file_uploader(
    "Upload your Walmart CSV file",
    type=["csv"]
)

if uploaded_file is None:
    st.info("Upload your Walmart CSV file to explore the dashboard.")
    st.stop()

try:
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()

    required_columns = [
        "Store", "Date", "Weekly_Sales", "Holiday_Flag"
    ]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        st.error(
            "Missing required columns: " + ", ".join(missing_columns)
        )
        st.stop()

    # Original Walmart CSV uses DD-MM-YYYY dates.
    df["Date"] = pd.to_datetime(
        df["Date"], format="%d-%m-%Y", errors="coerce"
    )

    for column in ["Store", "Weekly_Sales", "Holiday_Flag"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    invalid_rows = (
        df[required_columns].isna().any(axis=1)
        | ~df["Holiday_Flag"].isin([0, 1])
        | (df["Store"] < 1)
        | (df["Store"] % 1 != 0)
    )

    if invalid_rows.any():
        st.error(
            f"{int(invalid_rows.sum())} rows contain invalid or missing "
            "values. Check Store, Weekly_Sales, Holiday_Flag and Date. "
            "Dates must use DD-MM-YYYY format."
        )
        st.stop()

    if df.empty:
        st.warning("The uploaded file contains no data.")
        st.stop()

    df["Store"] = df["Store"].astype(int)
    df["Holiday_Flag"] = df["Holiday_Flag"].astype(int)
    df = df.sort_values(["Date", "Store"])

except (ValueError, pd.errors.ParserError, UnicodeDecodeError) as error:
    st.error(f"Unable to read this CSV file: {error}")
    st.stop()


# ---------- SIDEBAR FILTERS ----------
st.sidebar.header("Dashboard Filters")

store_options = ["All Stores"] + sorted(
    df["Store"].unique().tolist()
)

selected_store = st.sidebar.selectbox(
    "Select Store",
    options=store_options
)

min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if len(date_range) != 2:
    st.info("Please select both a start date and an end date.")
    st.stop()

start_date, end_date = date_range

filtered_df = df[
    df["Date"].between(
        pd.Timestamp(start_date),
        pd.Timestamp(end_date)
    )
].copy()

if selected_store != "All Stores":
    filtered_df = filtered_df[
        filtered_df["Store"] == selected_store
    ].copy()

if filtered_df.empty:
    st.warning("No sales data available for the selected filters.")
    st.stop()

st.sidebar.caption(
    f"Selected period: {start_date:%d %b %Y} "
    f"to {end_date:%d %b %Y}"
)
st.sidebar.caption(f"Rows displayed: {len(filtered_df):,}")


# ---------- SUMMARY CARDS ----------
total_sales = filtered_df["Weekly_Sales"].sum()
average_sales = filtered_df["Weekly_Sales"].mean()
number_of_stores = filtered_df["Store"].nunique()

col1, col2, col3 = st.columns(3)

col1.metric("Total Sales", f"{total_sales:,.2f}")
col2.metric(
    "Average Sales per Store-Week",
    f"{average_sales:,.2f}"
)
col3.metric("Number of Stores", number_of_stores)


# ---------- WEEKLY SALES TREND ----------
st.subheader("Weekly Sales Trend")

weekly_sales = (
    filtered_df.groupby("Date")["Weekly_Sales"]
    .sum()
    .sort_index()
    .rename("Total Weekly Sales")
)

st.line_chart(weekly_sales, use_container_width=True)

st.caption(
    "Total sales for each week across the selected stores."
)


# ---------- STORE COMPARISON ----------
st.subheader("Store-wise Total Sales")

store_sales = (
    filtered_df.groupby("Store")["Weekly_Sales"]
    .sum()
    .sort_index()
)

# Zero padding keeps stores in numeric order in the chart.
store_sales.index = [
    f"Store {store_id:02d}" for store_id in store_sales.index
]

st.bar_chart(
    store_sales.rename("Total Sales"),
    use_container_width=True
)


# ---------- HOLIDAY COMPARISON ----------
st.subheader("Holiday vs Non-Holiday: Average Sales per Store-Week")

holiday_sales = (
    filtered_df.groupby("Holiday_Flag")["Weekly_Sales"]
    .mean()
    .rename(index={0: "Non-Holiday", 1: "Holiday"})
    .rename("Average Sales")
)

st.bar_chart(holiday_sales, use_container_width=True)

st.caption(
    "Average sales per store-week for the selected stores and dates. "
    "Holiday classification follows the dataset's Holiday_Flag."
)

if len(holiday_sales) < 2:
    st.info(
        "This selection contains only one category. "
        "Select a wider date range to compare both."
    )


# ---------- SELECTED DATA INSIGHTS ----------
st.subheader("Sales Highlights")

best_store_sales = (
    filtered_df.groupby("Store")["Weekly_Sales"].sum()
)

best_store = int(best_store_sales.idxmax())
best_week = weekly_sales.idxmax()

st.write(
    f"• Highest total sales in this selection: "
    f"**Store {best_store}** "
    f"({best_store_sales.loc[best_store]:,.2f})."
)

st.write(
    f"• Highest combined weekly sales in this selection: "
    f"**{best_week:%d %b %Y}** "
    f"({weekly_sales.loc[best_week]:,.2f})."
)


# ---------- SALES DATA ----------
st.subheader("Sales Data")

display_df = filtered_df.sort_values(
    ["Store", "Date"]
).reset_index(drop=True)

# Format dates for display without changing the underlying data.
table_df = display_df.copy()
table_df["Date"] = table_df["Date"].dt.strftime("%d-%m-%Y")

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True
)


# ---------- DOWNLOAD ----------
csv_data = display_df.to_csv(
    index=False,
    date_format="%d-%m-%Y"
).encode("utf-8")

st.download_button(
    label="Download Filtered Sales Data",
    data=csv_data,
    file_name="walmart_filtered_sales.csv",
    mime="text/csv"
)

st.caption(
    "Historical sales analysis • "
    "All charts and downloads follow the selected filters."
)