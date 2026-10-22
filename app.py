from pathlib import Path
import re
from datetime import datetime
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, Image as ReportImage
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Astana Ria D'Raja | Analytics",
    page_icon="🏡",
    layout="wide",
)


# Refined visual design: premium black and gold dashboard
st.markdown("""
<style>
:root {
    --gold: #e5b95c;
    --gold-soft: #f2d48b;
    --panel: #15171c;
    --panel-alt: #1b1e25;
    --line: rgba(229, 185, 92, 0.24);
    --muted: #a9afbb;
}
.stApp {
    background:
        radial-gradient(ellipse at 12% 0%, rgba(229,185,92,.075), transparent 34%),
        #0b0c0f;
}
[data-testid="stHeader"] {
    background: rgba(11,12,15,.86);
}
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1500px;
}
h1, h2, h3 {
    letter-spacing: -0.025em;
}
h1 {
    color: #f7f4ec !important;
    font-weight: 800 !important;
}
h2, h3 {
    color: var(--gold-soft) !important;
    font-weight: 700 !important;
}
p, label, [data-testid="stMarkdownContainer"] {
    line-height: 1.55;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #151619 0%, #101114 100%);
    border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: var(--gold-soft) !important;
}
[data-testid="stMetric"] {
    background: linear-gradient(145deg, #1a1c22 0%, #121318 100%);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 16px 18px;
    min-height: 112px;
    box-shadow: 0 8px 24px rgba(0,0,0,.14);
}
[data-testid="stMetricLabel"] {
    color: #b9bec8 !important;
    font-size: .88rem !important;
}
[data-testid="stMetricValue"] {
    color: #fff8e8 !important;
    font-weight: 750 !important;
}
[data-testid="stMetricDelta"] {
    font-size: .82rem !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: rgba(229,185,92,.18) !important;
    border-radius: 14px !important;
}
div[data-testid="stExpander"] {
    border: 1px solid rgba(229,185,92,.2);
    border-radius: 12px;
    overflow: hidden;
}
div[data-testid="stExpander"] summary {
    background: rgba(255,255,255,.018);
}
.stButton > button, .stDownloadButton > button {
    border-radius: 10px;
    border: 1px solid rgba(229,185,92,.5);
    background: linear-gradient(135deg, #e5b95c 0%, #c99a39 100%);
    color: #17130a;
    font-weight: 700;
    transition: transform .15s ease, box-shadow .15s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    border-color: #f2d48b;
    box-shadow: 0 5px 18px rgba(229,185,92,.18);
    transform: translateY(-1px);
    color: #0b0c0f;
}
[data-baseweb="input"] > div,
[data-baseweb="select"] > div,
[data-baseweb="textarea"] > div {
    background: #111318 !important;
    border-color: #2c3039 !important;
    border-radius: 10px !important;
}
[data-baseweb="input"] input, [data-baseweb="textarea"] textarea {
    color: #f4f5f7 !important;
}
[data-baseweb="tag"] {
    background: #3a3020 !important;
    border: 1px solid rgba(229,185,92,.32) !important;
}
[data-testid="stDataFrame"], [data-testid="stTable"] {
    border: 1px solid #2c3039;
    border-radius: 12px;
    overflow: hidden;
}
hr {
    border-color: rgba(229,185,92,.18) !important;
}
div[data-testid="stAlert"] {
    border-radius: 12px;
}
[data-testid="stPlotlyChart"] {
    background: linear-gradient(145deg, rgba(255,255,255,.018), rgba(255,255,255,0));
    border: 1px solid rgba(255,255,255,.055);
    border-radius: 14px;
    padding: 8px;
}
</style>
""", unsafe_allow_html=True)


BASE_DIR = Path(__file__).parent
GOOGLE_SHEET_ID = "1C8tkN18UMDp7vLmGmnAmHg1ZydbmRCDWGIhqN_yV2Z8"
GOOGLE_SHEET_GID = 0

@st.cache_data(ttl=300)
def load_google_sheet():
    """Read the private Google Sheet using credentials stored in Streamlit Secrets."""
    service_account_info = dict(st.secrets["gcp_service_account"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    credentials = Credentials.from_service_account_info(
        service_account_info, scopes=scopes
    )
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    worksheet = spreadsheet.get_worksheet_by_id(GOOGLE_SHEET_GID)
    if worksheet is None:
        raise ValueError("Could not find the worksheet with gid=0 in the Google Sheet.")
    rows = worksheet.get_all_records()
    return pd.DataFrame(rows)

st.markdown(
    """
    <style>
    .stApp { background: #0b0b0d; color: #f5f5f5; }
    [data-testid="stSidebar"] { background: #141416; border-right: 1px solid #303034; }
    .main-title { font-size: 34px; font-weight: 750; color: #d8b46a; margin-bottom: 2px; }
    .subtitle { color: #a5a5ad; font-size: 14px; margin-bottom: 24px; }
    .metric-card { background: linear-gradient(135deg, #19191c, #111113); border: 1px solid #353238; border-radius: 14px; padding: 18px; min-height: 112px; }
    .metric-label { color: #aaa7af; font-size: 13px; margin-bottom: 9px; }
    .metric-value { color: #e2c27c; font-size: 26px; font-weight: 750; }
    .section-title { color: #e2c27c; font-size: 20px; font-weight: 650; margin-top: 16px; margin-bottom: 12px; }
    .note { color: #b9b9c1; background: #171719; padding: 12px 14px; border-radius: 9px; border-left: 3px solid #d8b46a; font-size: 13px; }
    div[data-testid="stDataFrame"] { border: 1px solid #353238; border-radius: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)

def money(value):
    return f"RM {value:,.2f}"

def metric_card(label, value):
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div></div>',
        unsafe_allow_html=True,
    )

def parse_date(value):
    if pd.isna(value):
        return pd.NaT
    if isinstance(value, (pd.Timestamp, datetime)):
        return pd.Timestamp(value)
    value = str(value).strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return pd.Timestamp(datetime.strptime(value, fmt))
        except ValueError:
            continue
    return pd.NaT

def parse_stay_dates(value):
    if pd.isna(value):
        return (pd.NaT, pd.NaT)
    match = re.search(
        r"(\d{1,2}/\d{1,2}/\d{2,4})\s*-\s*(\d{1,2}/\d{1,2}/\d{2,4})",
        str(value),
    )
    if not match:
        return (pd.NaT, pd.NaT)
    return (parse_date(match.group(1)), parse_date(match.group(2)))

st.markdown('<div class="main-title">ASTANA RIA D’RAJA</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Homestay Payment Analytics · Local Private Dashboard</div>',
    unsafe_allow_html=True,
)

try:
    raw = load_google_sheet()
except Exception as exc:
    st.error(
        "Unable to read the private Google Sheet. Check that Streamlit Secrets are saved, "
        "the service account email has Viewer access to the sheet, and the worksheet has gid=0. "
        f"Technical details: {exc}"
    )
    st.stop()

required = [
    "Recipt No.", "Date payment", "Check In and Out", "Duration",
    "Rooms & Bathrooms", "Status", "Amount (RM)", "Name", "Remarks sewa tarikh",
]
missing = [col for col in required if col not in raw.columns]
if missing:
    st.error(
        "This workbook does not have the expected updated columns: "
        + ", ".join(missing)
        + ". Keep the updated workbook beside app.py and check its column headings."
    )
    st.stop()

df = pd.DataFrame()
df["Receipt Number"] = raw["Recipt No."].astype("string").str.strip()
df["Payment Date"] = raw["Date payment"].apply(parse_date)
df["Check In and Out"] = raw["Check In and Out"].fillna("").astype(str)
stay_parsed = df["Check In and Out"].apply(parse_stay_dates)
df["Stay Start"] = stay_parsed.apply(lambda x: x[0])
df["Stay End"] = stay_parsed.apply(lambda x: x[1])
df["Duration"] = raw["Duration"].fillna("").astype(str).str.strip()
df["Rooms & Bathrooms"] = raw["Rooms & Bathrooms"].fillna("").astype(str).str.strip()
df["Status"] = raw["Status"].fillna("").astype(str).str.strip().str.upper()
df["Amount (RM)"] = pd.to_numeric(raw["Amount (RM)"], errors="coerce")
df["Customer Name"] = raw["Name"].fillna("").astype(str).str.strip()
df["Rental Remarks"] = raw["Remarks sewa tarikh"].fillna("").astype(str).str.strip()

# Standardize status labels for analysis while retaining the source label in the workbook.
status_map = {
    "DEPOSIT": "Deposit",
    "PENUH": "Full payment",
    "FULL PAYMENT": "Full payment",
    "FULL": "Full payment",
}
df["Payment Type"] = df["Status"].map(status_map).fillna("Unclassified")
df["Rooms"] = pd.to_numeric(
    df["Rooms & Bathrooms"].str.extract(r"(\d+)\s*BILIK", flags=re.IGNORECASE)[0],
    errors="coerce",
)
df["Bathrooms"] = pd.to_numeric(
    df["Rooms & Bathrooms"].str.extract(r"(\d+)\s*BILIK\s*AIR", flags=re.IGNORECASE)[0],
    errors="coerce",
)
df["Nights"] = (df["Stay End"] - df["Stay Start"]).dt.days
df["Payment Month"] = df["Payment Date"].dt.to_period("M").astype("string")

valid_payment = df.dropna(subset=["Payment Date", "Amount (RM)"]).copy()
if valid_payment.empty:
    st.error("No records have both a valid payment date and amount.")
    st.stop()

# Sidebar filters
st.sidebar.markdown("## Dashboard Filters")
st.sidebar.caption("Filters apply to the payment records and charts.")
min_date = valid_payment["Payment Date"].min().date()
max_date = valid_payment["Payment Date"].max().date()

# Allow the calendar to navigate beyond the current dataset's earliest/latest dates.
# The default selection still covers all recorded payment dates.
calendar_min_date = min_date.replace(year=max(1900, min_date.year - 10))
try:
    calendar_max_date = max_date.replace(year=min(2100, max_date.year + 10))
except ValueError:
    # Handle leap-day dates when extending the selectable calendar range.
    calendar_max_date = max_date.replace(year=min(2100, max_date.year + 10), day=28)

date_range = st.sidebar.date_input(
    "Payment date range",
    value=(min_date, max_date),
    min_value=calendar_min_date,
    max_value=calendar_max_date,
    help="Calendar navigation extends beyond the dates currently recorded. Selecting future dates will show no historical payments unless records exist.",
)
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

payment_types = sorted(valid_payment["Payment Type"].unique().tolist())
selected_types = st.sidebar.multiselect("Payment status", payment_types, default=payment_types)
room_values = sorted(valid_payment["Rooms"].dropna().unique().tolist())
selected_rooms = st.sidebar.multiselect(
    "Room configuration", room_values, default=room_values,
    format_func=lambda x: f"{int(x)} rooms",
)
search_customer = st.sidebar.text_input("Search customer name", placeholder="Enter customer name").strip()
search_receipt = st.sidebar.text_input("Search receipt number", placeholder="e.g. 65").strip()

filtered = valid_payment[
    (valid_payment["Payment Date"].dt.date >= start_date)
    & (valid_payment["Payment Date"].dt.date <= end_date)
    & (valid_payment["Payment Type"].isin(selected_types))
].copy()
if selected_rooms:
    filtered = filtered[filtered["Rooms"].isin(selected_rooms)]
else:
    filtered = filtered.iloc[0:0]
if search_customer:
    filtered = filtered[filtered["Customer Name"].str.contains(search_customer, case=False, regex=False, na=False)]
if search_receipt:
    filtered = filtered[filtered["Receipt Number"].str.contains(search_receipt, case=False, regex=False, na=False)]

# Executive summary
st.markdown('<div class="section-title">Executive Summary</div>', unsafe_allow_html=True)
if not filtered.empty:
    monthly_summary = filtered.assign(Month=filtered["Payment Date"].dt.to_period("M")).groupby("Month")["Amount (RM)"].sum().sort_index()
    best_month = monthly_summary.idxmax()
    deposit_records = filtered[filtered["Payment Type"] == "Deposit"]
    full_records = filtered[filtered["Payment Type"] == "Full payment"]
    a, b, c = st.columns(3)
    with a:
        st.metric("Highest payment month", best_month.strftime("%b %Y"))
        st.caption(f"Recorded payments: {money(monthly_summary.max())}")
    with b:
        st.metric("Deposit records", f"{len(deposit_records):,}")
        st.caption(f"Recorded deposit amount: {money(deposit_records['Amount (RM)'].sum())}")
    with c:
        st.metric("Full-payment records", f"{len(full_records):,}")
        st.caption(f"Recorded full-payment amount: {money(full_records['Amount (RM)'].sum())}")
    st.markdown("#### Automated observations")
    observations = [
        f"The current selection contains {len(filtered):,} payment records totalling {money(filtered['Amount (RM)'].sum())}."
    ]
    if len(monthly_summary) >= 2:
        latest_month = monthly_summary.index.max()
        previous_month = latest_month - 1
        if previous_month in monthly_summary.index and monthly_summary.loc[previous_month] != 0:
            change = (monthly_summary.loc[latest_month] - monthly_summary.loc[previous_month]) / monthly_summary.loc[previous_month] * 100
            direction = "increased" if change >= 0 else "decreased"
            observations.append(
                f"Recorded payments {direction} by {abs(change):.1f}% in {latest_month.strftime('%B %Y')} compared with {previous_month.strftime('%B %Y')}."
            )
    # Simple, transparent trend projection based on monthly recorded payments.
    # This is an indicative trend estimate, not a booking or profit forecast.
    if len(monthly_summary) >= 3:
        monthly_series = monthly_summary.copy()
        monthly_series.index = monthly_series.index.to_timestamp()
        monthly_series = monthly_series.groupby(monthly_series.index.to_period("M")).sum().sort_index()
        full_month_index = pd.period_range(monthly_series.index.min(), monthly_series.index.max(), freq="M")
        monthly_series = monthly_series.reindex(full_month_index, fill_value=0.0)
        recent = monthly_series.tail(12)
        y = recent.astype(float).tolist()
        n = len(y)
        x_mean = (n - 1) / 2
        y_mean = sum(y) / n
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = (sum((i - x_mean) * (value - y_mean) for i, value in enumerate(y)) / denominator) if denominator else 0.0
        next_values = [max(0.0, y_mean + slope * ((n - 1 + step) - x_mean)) for step in (1, 2, 3)]
        forecast_periods = pd.period_range(monthly_series.index.max() + 1, periods=3, freq="M")
        forecast_total = sum(next_values)
        if slope > max(1.0, abs(y_mean) * 0.03):
            trend_word = "upward"
        elif slope < -max(1.0, abs(y_mean) * 0.03):
            trend_word = "downward"
        else:
            trend_word = "fairly stable"
        observations.append(
            f"Indicative future trend: recorded payments may be {trend_word} over the next three months. "
            f"The simple trend-line estimate totals about {money(forecast_total)} across "
            f"{forecast_periods[0].strftime('%b %Y')} to {forecast_periods[-1].strftime('%b %Y')}."
        )
        forecast_df = pd.DataFrame({
            "Month": [period.to_timestamp() for period in list(recent.index) + list(forecast_periods)],
            "Amount (RM)": y + next_values,
            "Type": ["Recorded" for _ in y] + ["Estimated trend" for _ in next_values],
        })
        st.markdown("#### Future payment trend (estimate)")
        st.caption("Uses a simple linear trend from up to the last 12 months in the current filter selection. Estimates can be inaccurate, especially with few records, seasonal demand, or future bookings paid early.")
        trend_fig = px.line(
            forecast_df, x="Month", y="Amount (RM)", color="Type", markers=True,
            color_discrete_map={"Recorded": "#E5B95C", "Estimated trend": "#79A7FF"},
        )
        trend_fig.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=20, b=10), legend_title_text="",
            xaxis_title="Month", yaxis_title="Recorded payment amount (RM)",
        )
        st.plotly_chart(trend_fig, use_container_width=True)
    else:
        observations.append(
            "Future trend estimate is not shown yet: at least three months with recorded payments are needed for a basic trend projection."
        )
    observations.append(
        "Payment status is based on the source sheet's labels: DEPOSIT and PENUH. A payment record alone does not confirm that a stay was completed."
    )
    for item in observations:
        st.markdown(f"- {item}")
else:
    st.info("No records match the current filters.")

st.markdown('<div class="section-title">Payment Overview</div>', unsafe_allow_html=True)
total_payments = filtered["Amount (RM)"].sum()
record_count = len(filtered)
average_payment = filtered["Amount (RM)"].mean() if record_count else 0
deposit_amount = filtered.loc[filtered["Payment Type"] == "Deposit", "Amount (RM)"].sum()
k1, k2, k3, k4 = st.columns(4)
with k1:
    metric_card("RECORDED PAYMENTS", money(total_payments))
with k2:
    metric_card("PAYMENT RECORDS", f"{record_count:,}")
with k3:
    metric_card("AVERAGE PAYMENT", money(average_payment))
with k4:
    metric_card("DEPOSIT AMOUNT", money(deposit_amount))
st.markdown(
    '<div class="note">Figures represent recorded payment transactions, not verified profit or occupancy. A booking may have more than one payment record.</div>',
    unsafe_allow_html=True,
)

# Monthly chart
st.markdown('<div class="section-title">Monthly Recorded Payments</div>', unsafe_allow_html=True)
if filtered.empty:
    st.info("No records match the current filters.")
else:
    monthly = filtered.assign(Month=filtered["Payment Date"].dt.to_period("M").astype(str)).groupby(
        ["Month", "Payment Type"], as_index=False
    ).agg(Amount=("Amount (RM)", "sum"), Records=("Amount (RM)", "size"))
    fig = px.bar(
        monthly, x="Month", y="Amount", color="Payment Type", barmode="stack",
        title="Recorded payment amount by payment month",
        labels={"Month": "Payment month", "Amount": "Recorded payments (RM)", "Payment Type": "Payment status"},
        color_discrete_map={"Deposit": "#d8b46a", "Full payment": "#6888a5", "Unclassified": "#9a8b9e"},
    )
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0b0b0d", plot_bgcolor="#111113", margin=dict(l=15, r=15, t=60, b=15), legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)
with left:
    st.markdown('<div class="section-title">Payment Status Breakdown</div>', unsafe_allow_html=True)
    if filtered.empty:
        st.info("No data to display.")
    else:
        type_summary = filtered.groupby("Payment Type", as_index=False).agg(
            Amount=("Amount (RM)", "sum"), Records=("Amount (RM)", "size")
        )
        fig_type = px.pie(
            type_summary, names="Payment Type", values="Amount", hole=0.55,
            title="Share of recorded payment amounts", color="Payment Type",
            color_discrete_map={"Deposit": "#d8b46a", "Full payment": "#6888a5", "Unclassified": "#9a8b9e"},
        )
        fig_type.update_layout(template="plotly_dark", paper_bgcolor="#0b0b0d", plot_bgcolor="#111113")
        st.plotly_chart(fig_type, use_container_width=True)
        st.dataframe(type_summary.rename(columns={"Payment Type": "Payment status", "Amount": "Recorded amount (RM)"}), use_container_width=True, hide_index=True)

with right:
    st.markdown('<div class="section-title">Room Configuration</div>', unsafe_allow_html=True)
    room_data = filtered.dropna(subset=["Rooms"])
    if room_data.empty:
        st.info("No room configuration data for these filters.")
    else:
        room_summary = room_data.groupby("Rooms", as_index=False).agg(
            Amount=("Amount (RM)", "sum"), Records=("Amount (RM)", "size")
        ).sort_values("Rooms")
        fig_rooms = px.bar(room_summary, x="Rooms", y="Records", text="Records", title="Payment records by room count", labels={"Rooms": "Number of rooms", "Records": "Payment records"})
        fig_rooms.update_traces(marker_color="#d8b46a")
        fig_rooms.update_layout(template="plotly_dark", paper_bgcolor="#0b0b0d", plot_bgcolor="#111113", xaxis=dict(dtick=1))
        st.plotly_chart(fig_rooms, use_container_width=True)

# Data quality checks
st.markdown('<div class="section-title">Data Quality & Review</div>', unsafe_allow_html=True)
invalid_payment_dates = df[df["Payment Date"].isna()]
invalid_stays = df[df["Stay Start"].isna() | df["Stay End"].isna()]
invalid_nights = df[df["Nights"].notna() & (df["Nights"] < 0)]
missing_rooms = df[df["Rooms"].isna() | (df["Rooms & Bathrooms"].str.upper().str.strip().isin(["", "NIL", "N/A", "NA"]))]
future_payments = df[df["Payment Date"] > pd.Timestamp.today().normalize()]
unclassified = df[df["Payment Type"] == "Unclassified"]
receipt_counts = df["Receipt Number"].dropna().value_counts()
repeated_receipts = receipt_counts[receipt_counts > 1]

q1, q2, q3, q4, q5 = st.columns(5)
q1.metric("Invalid payment dates", len(invalid_payment_dates))
q2.metric("Invalid stay dates", len(invalid_stays))
q3.metric("Missing room details", len(missing_rooms))
q4.metric("Future-dated payments", len(future_payments))
q5.metric("Repeated receipt numbers", len(repeated_receipts))

with st.expander("View records requiring review"):
    if not invalid_payment_dates.empty:
        st.write("**Missing or invalid payment dates**")
        st.dataframe(raw.loc[invalid_payment_dates.index], use_container_width=True, hide_index=True)
    if not invalid_stays.empty:
        st.write("**Missing or invalid check-in/check-out dates**")
        st.dataframe(df.loc[invalid_stays.index, ["Receipt Number", "Customer Name", "Payment Date", "Check In and Out", "Amount (RM)"]], use_container_width=True, hide_index=True)
    if not invalid_nights.empty:
        st.write("**Check-out earlier than check-in**")
        st.dataframe(df.loc[invalid_nights.index, ["Receipt Number", "Customer Name", "Stay Start", "Stay End", "Nights"]], use_container_width=True, hide_index=True)
    if not missing_rooms.empty:
        st.write("**Missing or unrecognised room details**")
        st.dataframe(df.loc[missing_rooms.index, ["Receipt Number", "Customer Name", "Rooms & Bathrooms", "Amount (RM)"]], use_container_width=True, hide_index=True)
    if not future_payments.empty:
        st.write("**Payment dates later than today's date — verify, do not automatically delete**")
        st.dataframe(df.loc[future_payments.index, ["Receipt Number", "Payment Date", "Customer Name", "Amount (RM)"]], use_container_width=True, hide_index=True)
    if not repeated_receipts.empty:
        st.write("**Repeated receipt numbers — review, do not automatically delete**")
        repeated_df = df[df["Receipt Number"].isin(repeated_receipts.index)].sort_values("Receipt Number")
        st.dataframe(repeated_df[["Receipt Number", "Payment Date", "Customer Name", "Status", "Amount (RM)", "Rental Remarks"]], use_container_width=True, hide_index=True)
    if not unclassified.empty:
        st.write("**Payment status not recognised**")
        st.dataframe(df.loc[unclassified.index, ["Receipt Number", "Status", "Customer Name", "Amount (RM)"]], use_container_width=True, hide_index=True)
    if all(frame.empty for frame in [invalid_payment_dates, invalid_stays, invalid_nights, missing_rooms, future_payments, repeated_receipts.to_frame() if not repeated_receipts.empty else pd.DataFrame(), unclassified]):
        st.success("No data-quality review flags were detected by these checks.")

# Booking-level analysis: payment rows can have different receipt numbers.
st.markdown('<div class="section-title">Booking Analysis</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="note">Possible bookings are grouped using customer name, check-in date, check-out date, and room configuration. '
    'This is a matching estimate, not a guaranteed booking ID. Review matches before making payment decisions.</div>',
    unsafe_allow_html=True,
)

booking_source = df[
    df["Customer Name"].str.strip().ne("")
    & df["Stay Start"].notna()
    & df["Stay End"].notna()
    & df["Amount (RM)"].notna()
].copy()

booking_keys = ["Customer Name", "Stay Start", "Stay End", "Rooms & Bathrooms"]
booking_source["Booking Match Key"] = (
    booking_source["Customer Name"].str.casefold().str.replace(r"\s+", " ", regex=True)
    + "|"
    + booking_source["Stay Start"].dt.strftime("%Y-%m-%d")
    + "|"
    + booking_source["Stay End"].dt.strftime("%Y-%m-%d")
    + "|"
    + booking_source["Rooms & Bathrooms"].str.casefold().str.replace(r"\s+", " ", regex=True)
)
booking_source["Booking ID (estimated)"] = (
    "BKG-" + (booking_source.groupby("Booking Match Key", sort=True).ngroup() + 1).astype(str).str.zfill(3)
)

if booking_source.empty:
    st.info("There are no records with enough customer and stay-date information to estimate bookings.")
else:
    booking_summary = booking_source.groupby(
        ["Booking Match Key", "Booking ID (estimated)"], as_index=False
    ).agg(
        Customer=("Customer Name", "first"),
        Check_in=("Stay Start", "first"),
        Check_out=("Stay End", "first"),
        Room_configuration=("Rooms & Bathrooms", "first"),
        Payment_records=("Amount (RM)", "size"),
        Total_recorded_payments=("Amount (RM)", "sum"),
        Payment_statuses=("Payment Type", lambda values: ", ".join(sorted(set(values)))),
        Receipt_numbers=("Receipt Number", lambda values: ", ".join(values.dropna().astype(str).unique())),
    )
    booking_summary["Possible deposit-only"] = booking_summary["Payment_statuses"].apply(
        lambda value: "Review" if "Deposit" in value and "Full payment" not in value else ""
    )
    booking_summary["Booking payment status"] = booking_summary["Payment_statuses"].apply(
        lambda value: (
            "Deposit and full payment recorded"
            if "Deposit" in value and "Full payment" in value
            else "Deposit only — review"
            if "Deposit" in value and "Full payment" not in value
            else "Full payment recorded"
            if "Full payment" in value
            else "Unclassified — review"
        )
    )

    # Scope booking analysis by the payment-date, payment-type, room and text filters,
    # while grouping using all available records so the paired payment is not hidden by filters.
    matching_keys = set(booking_source["Booking Match Key"])
    visible_payment_keys = set(
        filtered.assign(
            **{
                "Booking Match Key": (
                    filtered["Customer Name"].str.casefold().str.replace(r"\s+", " ", regex=True)
                    + "|"
                    + filtered["Stay Start"].dt.strftime("%Y-%m-%d")
                    + "|"
                    + filtered["Stay End"].dt.strftime("%Y-%m-%d")
                    + "|"
                    + filtered["Rooms & Bathrooms"].str.casefold().str.replace(r"\s+", " ", regex=True)
                )
            }
        )["Booking Match Key"].dropna()
    )
    booking_view = booking_summary[booking_summary["Booking Match Key"].isin(visible_payment_keys)].copy()

    ba1, ba2, ba3, ba4 = st.columns(4)
    ba1.metric("Estimated bookings", f"{len(booking_view):,}")
    ba2.metric(
        "Bookings with deposit + full payment",
        f"{booking_view['Booking payment status'].eq('Deposit and full payment recorded').sum():,}",
    )
    ba3.metric(
        "Possible deposit-only (review)",
        f"{booking_view['Booking payment status'].eq('Deposit only — review').sum():,}",
    )
    ba4.metric(
        "Recorded payments across these bookings",
        money(booking_view["Total_recorded_payments"].sum()),
    )

    st.write("**Estimated booking summary**")
    summary_display = booking_view[
        [
            "Booking ID (estimated)", "Customer", "Check_in", "Check_out",
            "Room_configuration", "Payment_records", "Payment_statuses",
            "Total_recorded_payments", "Receipt_numbers", "Booking payment status",
        ]
    ].rename(
        columns={
            "Booking ID (estimated)": "Estimated booking ID",
            "Customer": "Customer name",
            "Check_in": "Check-in",
            "Check_out": "Check-out",
            "Room_configuration": "Rooms & bathrooms",
            "Payment_records": "Payment records",
            "Payment_statuses": "Payment statuses",
            "Total_recorded_payments": "Total recorded payments (RM)",
            "Receipt_numbers": "Receipt numbers",
            "Booking payment status": "Review status",
        }
    )
    st.dataframe(summary_display.sort_values(["Check-in", "Customer name"]), use_container_width=True, hide_index=True)

    with st.expander("View individual payment history for estimated bookings"):
        if not booking_view.empty:
            selected_booking = st.selectbox(
                "Choose estimated booking",
                booking_view["Booking ID (estimated)"].tolist(),
            )
            selected_key = booking_view.loc[
                booking_view["Booking ID (estimated)"].eq(selected_booking), "Booking Match Key"
            ].iloc[0]
            history = booking_source[booking_source["Booking Match Key"].eq(selected_key)].copy()
            history_display = history[
                [
                    "Receipt Number", "Payment Date", "Customer Name", "Payment Type",
                    "Amount (RM)", "Stay Start", "Stay End", "Rooms & Bathrooms", "Rental Remarks",
                ]
            ].rename(
                columns={
                    "Receipt Number": "Receipt number",
                    "Payment Date": "Payment date",
                    "Customer Name": "Customer name",
                    "Payment Type": "Payment status",
                    "Amount (RM)": "Amount (RM)",
                    "Stay Start": "Check-in",
                    "Stay End": "Check-out",
                    "Rooms & Bathrooms": "Rooms & bathrooms",
                    "Rental Remarks": "Remarks",
                }
            )
            st.dataframe(history_display.sort_values("Payment date"), use_container_width=True, hide_index=True)

    booking_csv = summary_display.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Download estimated booking summary (CSV)",
        data=booking_csv,
        file_name="astana_ria_estimated_booking_summary.csv",
        mime="text/csv",
    )


# Customer search and complete payment history
st.markdown('<div class="section-title">Customer Search & Payment History</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="note">Search independently of the sidebar filters to see all available records for a customer. '
    'Booking matches are estimates based on customer name, stay dates, and room configuration.</div>',
    unsafe_allow_html=True,
)

customer_records = df[df["Customer Name"].str.strip().ne("")].copy()
customer_names = sorted(customer_records["Customer Name"].dropna().unique().tolist(), key=str.casefold)

if not customer_names:
    st.info("No customer names are available in the workbook.")
else:
    customer_query = st.text_input(
        "Find a customer",
        placeholder="Type part of a customer name, e.g. Abuya",
        key="customer_history_search",
    ).strip()

    if customer_query:
        matching_names = [
            name for name in customer_names
            if customer_query.casefold() in name.casefold()
        ]
    else:
        matching_names = []

    if not customer_query:
        st.caption("Enter a name above to see the customer's bookings and complete payment history.")
    elif not matching_names:
        st.warning("No customer name matches that search.")
    else:
        chosen_customer = st.selectbox(
            "Select customer",
            matching_names,
            key="customer_history_select",
        )
        customer_history = customer_records[
            customer_records["Customer Name"].str.casefold().eq(chosen_customer.casefold())
        ].copy()

        # Group only this customer's records by estimated booking key.
        customer_history["Booking Match Key"] = (
            customer_history["Customer Name"].str.casefold().str.replace(r"\s+", " ", regex=True)
            + "|"
            + customer_history["Stay Start"].dt.strftime("%Y-%m-%d").fillna("unknown")
            + "|"
            + customer_history["Stay End"].dt.strftime("%Y-%m-%d").fillna("unknown")
            + "|"
            + customer_history["Rooms & Bathrooms"].str.casefold().str.replace(r"\s+", " ", regex=True)
        )
        customer_history["Booking ID (estimated)"] = (
            "BKG-" + (customer_history.groupby("Booking Match Key", sort=True).ngroup() + 1).astype(str).str.zfill(3)
        )

        total_recorded = customer_history["Amount (RM)"].sum(min_count=1)
        deposit_total = customer_history.loc[
            customer_history["Payment Type"].eq("Deposit"), "Amount (RM)"
        ].sum()
        full_total = customer_history.loc[
            customer_history["Payment Type"].eq("Full payment"), "Amount (RM)"
        ].sum()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Payment records", f"{len(customer_history):,}")
        c2.metric("Estimated stays", f"{customer_history['Booking Match Key'].nunique():,}")
        c3.metric("Recorded deposits", money(deposit_total))
        c4.metric("Recorded full payments", money(full_total))
        st.caption(f"Total recorded payments for {chosen_customer}: {money(total_recorded or 0)}")

        # Booking-level summary for the selected customer.
        customer_booking_summary = customer_history.groupby(
            ["Booking Match Key", "Booking ID (estimated)"], as_index=False
        ).agg(
            Check_in=("Stay Start", "first"),
            Check_out=("Stay End", "first"),
            Room_configuration=("Rooms & Bathrooms", "first"),
            Payment_records=("Amount (RM)", "size"),
            Total_recorded_payments=("Amount (RM)", "sum"),
            Payment_statuses=("Payment Type", lambda values: ", ".join(sorted(set(values)))),
            Receipt_numbers=("Receipt Number", lambda values: ", ".join(values.dropna().astype(str).unique())),
        )
        customer_booking_summary["Review status"] = customer_booking_summary["Payment_statuses"].apply(
            lambda value: (
                "Deposit and full payment recorded"
                if "Deposit" in value and "Full payment" in value
                else "Deposit only — review"
                if "Deposit" in value and "Full payment" not in value
                else "Full payment recorded"
                if "Full payment" in value
                else "Unclassified — review"
            )
        )
        st.write("**All estimated bookings for this customer**")
        customer_summary_display = customer_booking_summary.rename(columns={
            "Booking ID (estimated)": "Estimated booking ID",
            "Check_in": "Check-in",
            "Check_out": "Check-out",
            "Room_configuration": "Rooms & bathrooms",
            "Payment_records": "Payment records",
            "Payment_statuses": "Payment statuses",
            "Total_recorded_payments": "Total recorded payments (RM)",
            "Receipt_numbers": "Receipt numbers",
        })
        st.dataframe(
            customer_summary_display.sort_values(["Check-in", "Check-out"]),
            use_container_width=True,
            hide_index=True,
        )

        st.write("**Complete payment history**")
        history_columns = [
            "Receipt Number", "Payment Date", "Payment Type", "Amount (RM)",
            "Stay Start", "Stay End", "Duration", "Rooms & Bathrooms", "Rental Remarks",
        ]
        history_display = customer_history[history_columns].copy().rename(columns={
            "Receipt Number": "Receipt number",
            "Payment Date": "Payment date",
            "Payment Type": "Payment status",
            "Stay Start": "Check-in",
            "Stay End": "Check-out",
            "Duration": "Duration",
            "Rooms & Bathrooms": "Rooms & bathrooms",
            "Rental Remarks": "Remarks",
        })
        st.dataframe(
            history_display.sort_values("Payment date", ascending=False, na_position="last"),
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            "Download this customer's history (CSV)",
            data=history_display.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"astana_ria_customer_history_{re.sub(r'[^A-Za-z0-9_-]+', '_', chosen_customer).strip('_')}.csv",
            mime="text/csv",
            key="download_customer_history",
        )


# Records and export
st.markdown('<div class="section-title">Payment & Booking Records</div>', unsafe_allow_html=True)
display_columns = [
    "Receipt Number", "Payment Date", "Customer Name", "Stay Start", "Stay End",
    "Duration", "Rooms & Bathrooms", "Payment Type", "Amount (RM)", "Rental Remarks",
]
display_df = filtered[display_columns].copy().rename(columns={
    "Receipt Number": "Receipt number",
    "Payment Date": "Payment date",
    "Customer Name": "Customer name",
    "Stay Start": "Check-in",
    "Stay End": "Check-out",
    "Duration": "Duration",
    "Rooms & Bathrooms": "Rooms & bathrooms",
    "Payment Type": "Payment status",
    "Rental Remarks": "Remarks",
})
st.dataframe(display_df.sort_values("Payment date", ascending=False), use_container_width=True, hide_index=True)
csv_data = display_df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "Download filtered records (CSV)", data=csv_data,
    file_name="astana_ria_filtered_records.csv", mime="text/csv",
)
st.caption("Astana Ria D'Raja · Local analytics prototype · Keep customer information private.")


# Downloadable PDF report — uses the current sidebar-filtered selection.
def build_analysis_pdf():
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=14 * mm, leftMargin=14 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title="Astana Ria D'Raja Payment Analytics Report",
        author="Astana Ria D'Raja Analytics Dashboard",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=20, leading=24, textColor=colors.HexColor("#9A7428"),
        alignment=TA_LEFT, spaceAfter=4 * mm,
    ))
    styles.add(ParagraphStyle(
        name="SectionGold", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=12, leading=15, textColor=colors.HexColor("#9A7428"),
        spaceBefore=4 * mm, spaceAfter=2 * mm,
    ))
    styles.add(ParagraphStyle(
        name="SmallNote", parent=styles["BodyText"], fontSize=8, leading=10,
        textColor=colors.HexColor("#555555"), spaceAfter=2 * mm,
    ))
    styles.add(ParagraphStyle(
        name="CellText", parent=styles["BodyText"], fontSize=7, leading=8,
    ))
    story = []

    # Premium black-and-gold cover page.
    cover_brand = ParagraphStyle(
        "CoverBrand", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=27, leading=32, alignment=1,
        textColor=colors.HexColor("#F0D28A"), spaceAfter=8 * mm,
    )
    cover_title = ParagraphStyle(
        "CoverTitle", parent=styles["Heading2"], fontName="Helvetica",
        fontSize=17, leading=22, alignment=1,
        textColor=colors.white, spaceAfter=5 * mm,
    )
    cover_meta = ParagraphStyle(
        "CoverMeta", parent=styles["BodyText"], fontSize=10, leading=15,
        alignment=1, textColor=colors.HexColor("#E8E2D2"),
    )
    cover_kpi = ParagraphStyle(
        "CoverKPI", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=12, leading=16, alignment=1,
        textColor=colors.HexColor("#F0D28A"),
    )
    cover_details = [
        [Paragraph("ASTANA RIA D’RAJA", cover_brand)],
        [Paragraph("HOMESTAY PAYMENT ANALYTICS", cover_title)],
        [Paragraph("EXECUTIVE REPORT", cover_title)],
        [Spacer(1, 7 * mm)],
        [Paragraph(
            f"Reporting period: {start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')}<br/>"
            f"Generated: {datetime.now().strftime('%d %B %Y, %I:%M %p')}<br/>"
            "Source: Connected Google Sheet",
            cover_meta
        )],
        [Spacer(1, 9 * mm)],
        [Paragraph(
            f"RECORDED PAYMENTS: {money(filtered['Amount (RM)'].sum())}"
            f"&nbsp;&nbsp;&nbsp;&nbsp; | &nbsp;&nbsp;&nbsp;&nbsp;"
            f"PAYMENT RECORDS: {len(filtered):,}"
            f"&nbsp;&nbsp;&nbsp;&nbsp; | &nbsp;&nbsp;&nbsp;&nbsp;"
            f"AVERAGE PAYMENT: {money(filtered['Amount (RM)'].mean() if not filtered.empty else 0)}",
            cover_kpi
        )],
        [Spacer(1, 8 * mm)],
        [Paragraph("CONFIDENTIAL • BUSINESS ANALYTICS", cover_meta)],
    ]
    cover_table = Table(cover_details, colWidths=[landscape(A4)[0] - 28 * mm],
                        rowHeights=[24*mm, 13*mm, 12*mm, 7*mm, 27*mm, 9*mm, 22*mm, 8*mm, 12*mm])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#151515")),
        ("BOX", (0, 0), (-1, -1), 2, colors.HexColor("#C99A39")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(Spacer(1, 8 * mm))
    story.append(cover_table)
    story.append(PageBreak())

    story.append(Paragraph("ASTANA RIA D’RAJA", styles["ReportTitle"]))
    story.append(Paragraph("Homestay Payment Analytics — Executive Report", styles["Heading2"]))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%d %B %Y, %I:%M %p')} &nbsp;&nbsp; | &nbsp;&nbsp; "
        "Source: Connected Google Sheet", styles["SmallNote"]
    ))
    story.append(Paragraph("Report scope and filters", styles["SectionGold"]))
    story.append(Paragraph(
        f"Payment date range selected: {start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}. "
        f"Payment statuses: {', '.join(selected_types) if selected_types else 'None selected'}. "
        f"Room configurations: {', '.join(str(int(x)) for x in selected_rooms) if selected_rooms else 'None selected'}. "
        f"Customer search: {search_customer or 'All customers'}; receipt search: {search_receipt or 'All receipts'}. "
        "Unless otherwise stated, financial and monthly figures below use the current filtered payment records.",
        styles["SmallNote"]
    ))

    story.append(Paragraph("1. Key payment indicators", styles["SectionGold"]))
    kpi_rows = [
        ["Recorded payment total", "Payment records", "Average payment", "Deposit amount", "Full-payment amount"],
        [money(filtered["Amount (RM)"].sum()), f"{len(filtered):,}",
         money(filtered["Amount (RM)"].mean() if not filtered.empty else 0),
         money(filtered.loc[filtered["Payment Type"].eq("Deposit"), "Amount (RM)"].sum()),
         money(filtered.loc[filtered["Payment Type"].eq("Full payment"), "Amount (RM)"].sum())],
    ]
    kpi_table = Table(kpi_rows, colWidths=[48*mm, 35*mm, 40*mm, 42*mm, 45*mm], repeatRows=1)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#242424")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#F0D28A")),
        ("BACKGROUND", (0,1), (-1,-1), colors.HexColor("#F7F4EC")),
        ("TEXTCOLOR", (0,1), (-1,-1), colors.HexColor("#222222")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME", (0,1), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#C7B27D")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    story.append(kpi_table)

    story.append(Paragraph("2. Monthly recorded payment analysis", styles["SectionGold"]))
    if filtered.empty:
        story.append(Paragraph("No payment records match the selected filters.", styles["SmallNote"]))
    else:
        month_report = filtered.assign(Month=filtered["Payment Date"].dt.to_period("M").astype(str)).pivot_table(
            index="Month", columns="Payment Type", values="Amount (RM)", aggfunc="sum", fill_value=0
        ).sort_index()
        month_report["Total recorded payments"] = month_report.sum(axis=1)

        # Chart 1: monthly recorded payments, embedded directly in the PDF.
        chart_data = month_report["Total recorded payments"]
        chart_buffer = BytesIO()
        fig, ax = plt.subplots(figsize=(9.2, 3.0))
        chart_data.plot(kind="bar", ax=ax, color="#C99A39", edgecolor="#9A7428", width=0.72)
        ax.set_title("Monthly Recorded Payments", fontsize=12, fontweight="bold", color="#242424")
        ax.set_xlabel("Payment month")
        ax.set_ylabel("Amount (RM)")
        ax.grid(axis="y", linestyle="--", alpha=0.28)
        ax.set_axisbelow(True)
        ax.tick_params(axis="x", labelrotation=45, labelsize=7)
        ax.tick_params(axis="y", labelsize=8)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        fig.tight_layout()
        fig.savefig(chart_buffer, format="png", dpi=160, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        chart_buffer.seek(0)
        story.append(Spacer(1, 2 * mm))
        story.append(ReportImage(chart_buffer, width=245 * mm, height=79 * mm))
        story.append(Spacer(1, 2 * mm))

        monthly_rows = [["Month"] + [str(c) for c in month_report.columns]]
        for month, row in month_report.iterrows():
            monthly_rows.append([str(month)] + [money(row[c]) for c in month_report.columns])
        monthly_table = Table(monthly_rows, repeatRows=1, hAlign="LEFT")
        monthly_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#242424")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#F0D28A")),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 7),
            ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#D5D0C4")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F5F2EA")]),
            ("ALIGN", (1,1), (-1,-1), "RIGHT"),
            ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(monthly_table)

    story.append(Paragraph("3. Payment status breakdown", styles["SectionGold"]))
    if filtered.empty:
        story.append(Paragraph("No status breakdown is available for the current selection.", styles["SmallNote"]))
    else:
        status_summary = filtered.groupby("Payment Type", as_index=False).agg(
            Records=("Amount (RM)", "size"), Amount=("Amount (RM)", "sum")
        )
        # Chart 2: payment-status amounts, embedded directly in the PDF.
        status_chart_buffer = BytesIO()
        fig, ax = plt.subplots(figsize=(6.8, 2.8))
        status_plot = status_summary.set_index("Payment Type")["Amount"]
        status_colors = ["#C99A39" if str(label).lower() == "deposit" else "#3B6D8C"
                         for label in status_plot.index]
        status_plot.plot(kind="bar", ax=ax, color=status_colors, edgecolor="#333333", width=0.62)
        ax.set_title("Recorded Amount by Payment Status", fontsize=11, fontweight="bold", color="#242424")
        ax.set_xlabel("")
        ax.set_ylabel("Amount (RM)")
        ax.grid(axis="y", linestyle="--", alpha=0.28)
        ax.set_axisbelow(True)
        ax.tick_params(axis="x", labelrotation=0, labelsize=8)
        ax.tick_params(axis="y", labelsize=8)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        fig.tight_layout()
        fig.savefig(status_chart_buffer, format="png", dpi=160, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        status_chart_buffer.seek(0)
        story.append(ReportImage(status_chart_buffer, width=165 * mm, height=68 * mm))
        story.append(Spacer(1, 2 * mm))

        status_rows = [["Payment status", "Record count", "Recorded amount"]]
        for _, r in status_summary.iterrows():
            status_rows.append([str(r["Payment Type"]), f"{int(r['Records']):,}", money(r["Amount"])])
        status_table = Table(status_rows, colWidths=[70*mm, 40*mm, 55*mm], repeatRows=1)
        status_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#242424")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#F0D28A")),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#D5D0C4")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F5F2EA")]),
            ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(status_table)

    story.append(Paragraph("4. Estimated booking analysis", styles["SectionGold"]))
    if "booking_view" in globals() and isinstance(booking_view, pd.DataFrame):
        if booking_view.empty:
            story.append(Paragraph("No estimated bookings match the current filtered payment records.", styles["SmallNote"]))
        else:
            story.append(Paragraph(
                f"Estimated bookings in scope: {len(booking_view):,}; "
                f"deposit and full payment recorded: {booking_view['Booking payment status'].eq('Deposit and full payment recorded').sum():,}; "
                f"possible deposit-only bookings requiring review: {booking_view['Booking payment status'].eq('Deposit only — review').sum():,}.",
                styles["SmallNote"]
            ))
            booking_rows = [["Estimated ID", "Customer", "Check-in", "Check-out", "Rooms", "Records", "Recorded total", "Review status"]]
            for _, r in booking_view.sort_values(["Check_in", "Customer"], na_position="last").head(100).iterrows():
                booking_rows.append([
                    str(r.get("Booking ID (estimated)", "")),
                    str(r.get("Customer", ""))[:28],
                    r["Check_in"].strftime("%d %b %Y") if pd.notna(r["Check_in"]) else "—",
                    r["Check_out"].strftime("%d %b %Y") if pd.notna(r["Check_out"]) else "—",
                    str(r.get("Room_configuration", "")),
                    str(r.get("Payment_records", "")),
                    money(r.get("Total_recorded_payments", 0)),
                    str(r.get("Booking payment status", ""))[:35],
                ])
            booking_table = Table(booking_rows, colWidths=[23*mm, 39*mm, 25*mm, 25*mm, 24*mm, 17*mm, 32*mm, 45*mm], repeatRows=1)
            booking_table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#242424")),
                ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#F0D28A")),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 6.5),
                ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#D5D0C4")),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F5F2EA")]),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ]))
            story.append(booking_table)
            if len(booking_view) > 100:
                story.append(Paragraph("Note: The PDF lists the first 100 estimated bookings; use the dashboard CSV export for the complete table.", styles["SmallNote"]))
    else:
        story.append(Paragraph("Booking analysis was not available when this report was generated.", styles["SmallNote"]))

    story.append(Paragraph("5. Data quality checks", styles["SectionGold"]))
    quality_rows = [
        ["Check", "Records flagged"],
        ["Invalid payment dates", f"{len(invalid_payment_dates):,}"],
        ["Invalid or missing stay dates", f"{len(invalid_stays):,}"],
        ["Missing or unrecognised room details", f"{len(missing_rooms):,}"],
        ["Future-dated payment records", f"{len(future_payments):,}"],
        ["Repeated receipt numbers", f"{len(repeated_receipts):,}"],
        ["Unclassified payment status", f"{len(unclassified):,}"],
    ]
    quality_table = Table(quality_rows, colWidths=[100*mm, 40*mm], repeatRows=1)
    quality_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#242424")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#F0D28A")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 8),
        ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#D5D0C4")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F5F2EA")]),
        ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(quality_table)

    story.append(Paragraph("6. Automated observations and future trend", styles["SectionGold"]))
    if not filtered.empty:
        story.append(Paragraph(
            f"Highest recorded payment month in the current selection: {best_month.strftime('%B %Y')} "
            f"({money(monthly_summary.max())}).", styles["SmallNote"]
        ))
        for observation in observations:
            story.append(Paragraph("• " + str(observation), styles["SmallNote"]))
    else:
        story.append(Paragraph("No automated observations are available because the selection contains no records.", styles["SmallNote"]))

    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Important interpretation note: these figures represent recorded payment transactions, not verified profit or occupancy. "
        "A booking may have multiple payment records. Estimated booking matches and future trend projections are indicative and should be reviewed before business decisions.",
        styles["SmallNote"]
    ))

    def add_page_number(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#777777"))
        canvas.drawRightString(landscape(A4)[0] - 14*mm, 7*mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    buffer.seek(0)
    return buffer.getvalue()

st.markdown('<div class="section-title">Download Analysis Report</div>', unsafe_allow_html=True)
st.caption("Create a PDF executive report containing key payment indicators, monthly analysis, payment-status breakdown, estimated booking summary, data-quality checks, and automated observations for the current filters.")
try:
    pdf_bytes = build_analysis_pdf()
    st.download_button(
        "Download analysis report (PDF)",
        data=pdf_bytes,
        file_name=f"astana_ria_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
        mime="application/pdf",
        help="The report reflects the currently selected dashboard filters.",
        key="download_analysis_pdf",
    )
except Exception as pdf_error:
    st.error(f"Could not generate the PDF report: {pdf_error}. If ReportLab is not installed, run: python -m pip install reportlab")
