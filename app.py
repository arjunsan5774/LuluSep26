"""
LuLu UAE Sales Dashboard  (app.py)
==================================
A Streamlit dashboard built on SYNTHETIC (made-up) LuLu-style sales data.

How the filters work
--------------------
1. GLOBAL filters (date range + emirates) sit in the box at the top.
   They change EVERY chart on the page.
2. LOCAL filters sit behind the "Filters" button on each chart.
   They change ONLY that one chart, on top of the global filters.

Why each chart is wrapped in @st.fragment
-----------------------------------------
Normally, touching ANY widget makes Streamlit re-run the whole script.
A "fragment" is a piece of the page that can re-run on its own.
So when you change a chart's local filter, only that chart is redrawn.

Run it on your own computer:
    pip install -r requirements.txt
    streamlit run app.py
"""

import random
from datetime import timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# =============================================================================
# 1. PAGE SETUP  (must be the first Streamlit command in the file)
# =============================================================================
st.set_page_config(page_title="LuLu UAE Sales Dashboard", page_icon="🌌", layout="wide")

# ---- STARRY NIGHT THEME -----------------------------------------------------
# Stars are tiny boxes whose box-shadows draw hundreds of dots; CSS animations make them twinkle.
def star_field(count, seed):
    rnd = random.Random(seed)
    colours = ["#ffffff", "#ffe3e6", "#d6e4ff"]
    return ",".join(f"{rnd.randint(0, 100)}vw {rnd.randint(0, 100)}vh {rnd.choice(colours)}" for _ in range(count))


THEME_CSS = f"""
<style>
html, body {{ background: radial-gradient(circle at 88% 10%, rgba(255,240,200,.28) 0, rgba(255,240,200,0) 7%),
              linear-gradient(180deg, #03050f 0%, #0a1030 55%, #1d1245 100%) fixed !important; }}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{ background: transparent !important; }}
[data-testid="stSidebar"] {{ background: rgba(5,8,24,.72) !important; backdrop-filter: blur(8px); }}
.block-container {{ position: relative; z-index: 1; }}
.stars {{ position: fixed; top: 0; left: 0; border-radius: 50%; pointer-events: none; z-index: 0; }}
.s1 {{ width: 1px; height: 1px; box-shadow: {star_field(160, 1)}; animation: twinkle 4s ease-in-out infinite; }}
.s2 {{ width: 2px; height: 2px; box-shadow: {star_field(60, 2)}; animation: twinkle 6s ease-in-out 1s infinite; }}
.s3 {{ width: 3px; height: 3px; box-shadow: {star_field(18, 3)}; animation: twinkle 3s ease-in-out .5s infinite; }}
.shoot {{ position: fixed; top: 8vh; left: 85vw; width: 140px; height: 2px; opacity: 0; pointer-events: none; z-index: 0;
         background: linear-gradient(90deg, #fff, transparent); animation: shoot 11s ease-in infinite; }}
@keyframes twinkle {{ 0%,100% {{ opacity: .95 }} 50% {{ opacity: .25 }} }}
@keyframes shoot {{ 0% {{ opacity: 0; transform: translate(0,0) rotate(35deg) }} 2% {{ opacity: 1 }}
                   9% {{ opacity: 0; transform: translate(-55vw,38vh) rotate(35deg) }} 100% {{ opacity: 0 }} }}
@keyframes rise {{ from {{ opacity: 0; transform: translateY(22px) }} to {{ opacity: 1; transform: none }} }}
@keyframes fade {{ from {{ opacity: 0 }} to {{ opacity: 1 }} }}
h1, h2, h3, h4 {{ color: #ff4d5a !important; text-shadow: 0 0 18px rgba(255,77,90,.45); }}
p, label, li, [data-testid="stCaptionContainer"] {{ color: #fff; }}
[data-testid="stMetricValue"] {{ color: #ff4d5a !important; }}
[data-testid="stMetricLabel"] p {{ color: #fff !important; }}
[data-testid="stMain"] .block-container > div {{ animation: rise .6s ease both; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ background: rgba(12,18,48,.55); backdrop-filter: blur(6px);
    border: 1px solid rgba(255,255,255,.16) !important; border-radius: 14px; transition: box-shadow .3s, border-color .3s; }}
[data-testid="stVerticalBlockBorderWrapper"]:hover {{ border-color: rgba(255,77,90,.6) !important; box-shadow: 0 6px 28px rgba(255,77,90,.22); }}
[data-testid="stPlotlyChart"], [data-testid="stDataFrame"] {{ animation: fade .8s ease both; }}
.stButton button, [data-testid="stPopover"] button {{ border: 1px solid #ff4d5a; color: #fff; transition: all .25s; }}
.stButton button:hover, [data-testid="stPopover"] button:hover {{ background: #ff4d5a; color: #fff; transform: scale(1.05); }}
</style>
<div class="stars s1"></div><div class="stars s2"></div><div class="stars s3"></div><div class="shoot"></div>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)

# =============================================================================
# 2. SETTINGS USED ACROSS THE APP
# =============================================================================
# The CSV sits in the same folder as this file. Building the path from
# __file__ means it is found both on your laptop and on Streamlit Cloud.
DATA_FILE = Path(__file__).parent / "lulu_sales_data.csv"

CATEGORIES = ["Fresh", "Grocery", "Fashion", "Home Decor", "Electronics", "Furniture"]
EMIRATES = ["Dubai", "Abu Dhabi", "Sharjah", "Ajman", "Ras Al Khaimah", "Fujairah", "Umm Al Quwain"]
AGE_GROUPS = ["18-24", "25-34", "35-44", "45-54", "55+"]
FESTIVE_SEASONS = ["White Friday", "DSF", "Ramadan", "Back to School"]

# Each category always gets the SAME colour in every chart, so viewers
# learn the colours once and can read every chart faster.
CATEGORY_COLORS = {
    "Fresh": "#2E9E5B",
    "Grocery": "#E0A526",
    "Fashion": "#C2408A",
    "Home Decor": "#2A9D8F",
    "Electronics": "#3A6FD8",
    "Furniture": "#D9955F",
}
OTHER_COLORS = ["#3A6FD8", "#2A9D8F", "#E0A526", "#C2408A"]   # for charts not split by category
CHART_HEIGHT = 380                                          # same height for every chart

# The measures a user can choose, and the column each one comes from.
METRIC_COLUMNS = {
    "Net sales (AED)": "Net_Sales_AED",
    "Profit (AED)": "Profit_AED",
    "Units sold": "Units_Sold",
    "Transactions": "Transaction_ID",
}


# =============================================================================
# 3. LOAD THE DATA
# =============================================================================
# @st.cache_data = "read the file once, then remember it".
# Without it, the CSV would be re-read every time anyone clicks anything.
#
# ➡️ LIVE VERSION (later): change this to @st.cache_data(ttl=5)
#    so Streamlit re-reads the file every 5 seconds and picks up new rows.
@st.cache_data
def load_data():
    if DATA_FILE.exists():
        return pd.read_csv(DATA_FILE, parse_dates=["Timestamp", "Date"])
    return pd.read_excel(DATA_FILE.with_name("lulu_sales_data_csv.xlsx"))   # fallback: the Excel file


# =============================================================================
# 4. HELPER FUNCTIONS  (small reusable pieces used by the charts)
# =============================================================================
def aed(value):
    """Turn a number into a short money label, e.g. 1234567 -> 'AED 1.23M'."""
    if abs(value) >= 1_000_000:
        return f"AED {value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"AED {value / 1_000:.1f}K"
    return f"AED {value:,.0f}"


def filter_rows(data, start, end, emirates):
    """Keep only rows between two dates AND inside the chosen emirates."""
    in_dates = data["Date"].between(pd.Timestamp(start), pd.Timestamp(end))
    in_emirates = data["Emirate"].isin(emirates)
    return data[in_dates & in_emirates]


def chosen_emirates():
    """Emirates picked in the global filter. Picking nothing means 'all emirates'."""
    return st.session_state["global_emirates"] or EMIRATES


def get_global_data():
    """Every chart starts here: the full data with the GLOBAL filters applied.

    The global widgets save their values in st.session_state (Streamlit's
    memory), so any chart can read them, even when only that chart re-runs.
    """
    start, end = st.session_state["global_dates"]
    return filter_rows(load_data(), start, end, chosen_emirates())


def emirates_in(data):
    """Emirates that appear in the data, in our standard order."""
    present = set(data["Emirate"])
    return [e for e in EMIRATES if e in present]


def summarise(data, group_by, metric):
    """Group the data (e.g. by Category) and calculate one measure per group.

    Most measures are simple totals. Two need special maths:
      * Transactions      -> count the rows
      * Profit margin (%) -> total profit / total net sales x 100
      * Average rating    -> the average (mean) of the ratings
    """
    groups = data.groupby(group_by)
    if metric == "Transactions":
        result = groups["Transaction_ID"].count()
    elif metric == "Profit margin (%)":
        result = groups["Profit_AED"].sum() / groups["Net_Sales_AED"].sum() * 100
    elif metric == "Average rating (1-5)":
        result = groups["Customer_Rating"].mean()
    else:
        result = groups[METRIC_COLUMNS[metric]].sum()
    return result.rename(metric).reset_index()


def card_header(title, wide=False):
    """Draw a chart title with a 'Filters' button on its right.

    Returns the pop-over (the little menu that opens when you click the
    button). Anything created inside  `with card_header(...):`  goes in it.
    """
    title_col, button_col = st.columns([6, 1] if wide else [3, 1], vertical_alignment="center")
    title_col.markdown(f"#### {title}")
    return button_col.popover("Filters", icon=":material/tune:", width="stretch")


def local_select(label, options, key):
    """A dropdown that never gets 'stuck' on an option that has disappeared.

    Example: you pick 'Ajman' in a chart, then remove Ajman in the global
    filter. The old choice is no longer valid, so we reset it to the first
    option ('All ...') before drawing the dropdown.
    """
    if st.session_state.get(key) not in options:
        st.session_state[key] = options[0]
    return st.selectbox(label, options, key=key)


def show_active_filters(*choices):
    """The filters hide inside a pop-over, so print the current choices under the title."""
    st.caption("Showing: " + ", ".join(choices))


def no_data_message():
    st.info("No transactions match these filters. Widen them using the Filters button.")


def style(fig):
    """Give every Plotly chart the same size, margins and legend position."""
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ffffff"), transition=dict(duration=700, easing="cubic-in-out"),
        height=CHART_HEIGHT,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text=""),
    )
    return fig


# =============================================================================
# 5. THE CHARTS
# Each function below draws one card: title + Filters button + chart.
# @st.fragment lets each card re-run on its own when its local filters change.
#
# ➡️ LIVE VERSION (later): change @st.fragment to @st.fragment(run_every="5s")
#    and the card will refresh itself every 5 seconds.
# =============================================================================

# ----------------------------------------------------------------- KPI strip
def calc_kpis(data):
    """The five headline numbers for a slice of data."""
    net = data["Net_Sales_AED"].sum()
    count = len(data)
    return {
        "net": net,
        "transactions": count,
        "units": data["Units_Sold"].sum(),
        "avg_value": net / count if count else 0,
        "margin": data["Profit_AED"].sum() / net * 100 if net else 0,
    }


def pct_change(now, before):
    """'+12.3%' style change label, or None when there is nothing to compare with."""
    if before is None or before == 0:
        return None
    return f"{(now - before) / abs(before) * 100:+.1f}%"


@st.fragment
def kpi_row():
    data = get_global_data()

    # Compare with the period just before, of the same length.
    # (With the full year selected there is no earlier data, so no arrows.)
    start, end = st.session_state["global_dates"]
    period_days = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_days - 1)
    previous = filter_rows(load_data(), prev_start, prev_end, chosen_emirates())

    now = calc_kpis(data)
    before = calc_kpis(previous) if not previous.empty else {k: None for k in now}

    # Month-by-month values for the small sparkline inside each KPI box
    by_month = data.groupby(data["Date"].dt.to_period("M"))
    monthly_net = by_month["Net_Sales_AED"].sum()
    monthly_count = by_month["Transaction_ID"].count()
    sparklines = {
        "net": monthly_net.round(0).tolist(),
        "transactions": monthly_count.tolist(),
        "units": by_month["Units_Sold"].sum().tolist(),
        "avg_value": (monthly_net / monthly_count).round(1).tolist(),
        "margin": (by_month["Profit_AED"].sum() / monthly_net * 100).round(1).tolist(),
    }

    margin_delta = None if before["margin"] is None else f"{now['margin'] - before['margin']:+.1f} pts"
    compare_help = "Arrow = change vs the previous period of the same length (shown when that period is in the data)."

    boxes = [
        ("Net sales", aed(now["net"]), pct_change(now["net"], before["net"]), "net"),
        ("Transactions", f"{now['transactions']:,}", pct_change(now["transactions"], before["transactions"]), "transactions"),
        ("Units sold", f"{now['units']:,}", pct_change(now["units"], before["units"]), "units"),
        ("Avg. transaction value", aed(now["avg_value"]), pct_change(now["avg_value"], before["avg_value"]), "avg_value"),
        ("Profit margin", f"{now['margin']:.1f}%", margin_delta, "margin"),
    ]
    for column, (label, value, delta, spark_key) in zip(st.columns(5), boxes):
        column.metric(label, value, delta, border=True, help=compare_help,
                      chart_data=sparklines[spark_key], chart_type="area")


# --------------------------------------------------------- Sales by category
@st.fragment
def sales_by_category_card():
    data = get_global_data()
    with st.container(border=True):
        with card_header("Sales by category"):
            emirate = local_select("Emirate", ["All emirates"] + emirates_in(data), key="cat_emirate")
            metric = st.radio("Measure", list(METRIC_COLUMNS), key="cat_metric")
        view = st.segmented_control("View as", ["Bar", "Donut", "Treemap"], default="Bar", required=True, key="cat_view")

        if emirate != "All emirates":
            data = data[data["Emirate"] == emirate]
        show_active_filters(emirate, metric)
        if data.empty:
            return no_data_message()

        summary = summarise(data, "Category", metric)
        if view != "Bar" and (summary[metric] <= 0).any():
            view = "Bar"   # pies and treemaps cannot show zero or negative values
        if view == "Donut":
            fig = px.pie(summary, names="Category", values=metric, hole=0.55, color="Category",
                         color_discrete_map=CATEGORY_COLORS)
            fig.update_traces(textinfo="percent+label")
        elif view == "Treemap":
            fig = px.treemap(summary, path=["Category"], values=metric, color="Category",
                             color_discrete_map=CATEGORY_COLORS)
            fig.update_traces(textinfo="label+percent root")
        else:
            fig = px.bar(summary, x=metric, y="Category", orientation="h", text_auto=".3s",
                         color="Category", color_discrete_map=CATEGORY_COLORS)
            fig.update_yaxes(categoryorder="total ascending")   # biggest bar at the top
        fig.update_layout(showlegend=False, yaxis_title=None)
        st.plotly_chart(style(fig), key="chart_category")


# ------------------------------------------------- Emirate x Category heatmap
@st.fragment
def emirate_heatmap_card():
    data = get_global_data()
    with st.container(border=True):
        with card_header("Emirate × category heatmap"):
            metric = st.radio("Measure", ["Net sales (AED)", "Profit (AED)", "Profit margin (%)", "Transactions"],
                              key="heat_metric")
            channel = st.selectbox("Sales channel", ["All channels", "In-store", "Online", "Click & Collect"],
                                   key="heat_channel")

        if channel != "All channels":
            data = data[data["Sales_Channel"] == channel]
        show_active_filters(metric, channel)
        if data.empty:
            return no_data_message()

        # Turn the long table into a grid: one row per emirate, one column per category
        grid = (summarise(data, ["Emirate", "Category"], metric)
                .pivot(index="Emirate", columns="Category", values=metric)
                .reindex(index=emirates_in(data), columns=CATEGORIES))

        is_margin = metric == "Profit margin (%)"
        if not is_margin:
            grid = grid.fillna(0)   # no sales = 0 (a margin with no sales is left blank)

        fig = px.imshow(
            grid, aspect="auto",
            text_auto=".1f" if is_margin else ".3s",
            # Margin can be negative, so use red-yellow-green centred on 0
            color_continuous_scale="RdYlGn" if is_margin else "Greens",
            color_continuous_midpoint=0 if is_margin else None,
            labels=dict(x="", y="", color=""),
        )
        st.plotly_chart(style(fig), key="chart_heatmap")


# ------------------------------------------------------------ Sales over time
@st.fragment
def trend_card():
    data = get_global_data()
    with st.container(border=True):
        with card_header("Sales over time", wide=True):
            chosen = st.multiselect("Categories", CATEGORIES, placeholder="All categories", key="trend_categories")
            grain = st.segmented_control("Group dates by", ["Daily", "Weekly", "Monthly"],
                                         default="Monthly", required=True, key="trend_grain")
            metric = st.radio("Measure", ["Net sales (AED)", "Profit (AED)", "Units sold", "Transactions"],
                              key="trend_metric")
            split = st.toggle("One line per category", value=True, key="trend_split")
            show_seasons = st.toggle("Shade festive seasons", value=True, key="trend_seasons")
        kind = st.segmented_control("Chart type", ["Line", "Area", "Bar"], default="Line", required=True, key="trend_kind")

        if chosen:
            data = data[data["Category"].isin(chosen)]
        show_active_filters(", ".join(chosen) if chosen else "All categories", grain, metric)
        if data.empty:
            return no_data_message()

        # Put every date into a bucket: its day, its week or its month
        freq = {"Daily": "D", "Weekly": "W", "Monthly": "M"}[grain]
        data = data.assign(Period=data["Date"].dt.to_period(freq).dt.start_time)

        summary = summarise(data, ["Period", "Category"] if split else "Period", metric)
        args = dict(x="Period", y=metric, color="Category" if split else None,
                    category_orders={"Category": CATEGORIES}, color_discrete_map=CATEGORY_COLORS,
                    color_discrete_sequence=["#ff4d5a"])
        if kind == "Line":
            fig = px.line(summary, markers=grain != "Daily", **args)
        else:
            fig = {"Area": px.area, "Bar": px.bar}[kind](summary, **args)
        fig.update_layout(xaxis_title=None)

        if show_seasons:
            # Find each season's first and last day from the Promotion column
            everything = load_data()
            first_shown, last_shown = data["Date"].min(), data["Date"].max()
            for season in FESTIVE_SEASONS:
                days = everything.loc[everything["Promotion"] == season, "Date"]
                if days.max() >= first_shown and days.min() <= last_shown:   # only if it's in view
                    fig.add_vrect(x0=days.min(), x1=days.max(), fillcolor="#E0A526", opacity=0.12,
                                  line_width=0, annotation_text=season, annotation_position="top left",
                                  annotation_font_size=11)

        st.plotly_chart(style(fig), key="chart_trend")


# --------------------------------------------------- Channel / payment mix
@st.fragment
def mix_card():
    data = get_global_data()
    with st.container(border=True):
        with card_header("How customers buy and pay"):
            view = st.radio("Break down by", ["Sales channel", "Payment method"], key="mix_view")
            category = st.selectbox("Category", ["All categories"] + CATEGORIES, key="mix_category")
            metric = st.radio("Measure", ["Net sales (AED)", "Transactions"], key="mix_metric")

        if category != "All categories":
            data = data[data["Category"] == category]
        show_active_filters(view, category, metric)
        if data.empty:
            return no_data_message()

        column = "Sales_Channel" if view == "Sales channel" else "Payment_Method"
        summary = summarise(data, column, metric)
        fig = px.pie(summary, names=column, values=metric, hole=0.55,
                     color_discrete_sequence=OTHER_COLORS)
        fig.update_traces(textinfo="percent", sort=True)
        st.plotly_chart(style(fig), key="chart_mix")


# ------------------------------------------------------ Promotion impact
@st.fragment
def promotion_card():
    data = get_global_data()
    with st.container(border=True):
        with card_header("Do deeper discounts cost margin?"):
            category = st.selectbox("Category", ["All categories"] + CATEGORIES, key="promo_category")
            emirate = local_select("Emirate", ["All emirates"] + emirates_in(data), key="promo_emirate")

        if category != "All categories":
            data = data[data["Category"] == category]
        if emirate != "All emirates":
            data = data[data["Emirate"] == emirate]
        show_active_filters(category, emirate)
        if data.empty:
            return no_data_message()

        groups = data.groupby("Promotion")
        summary = pd.DataFrame({
            "Avg. discount (%)": groups["Discount_Pct"].mean(),
            "Profit margin (%)": groups["Profit_AED"].sum() / groups["Net_Sales_AED"].sum() * 100,
            "Transactions": groups["Transaction_ID"].count(),
        }).sort_values("Avg. discount (%)").reset_index()

        # Show how many transactions sit behind each bar (n=...). Few transactions
        # = a less reliable bar, and it is honest to show that.
        summary["Promotion"] = summary["Promotion"] + "<br>(n=" + summary["Transactions"].astype(str) + ")"

        # Reshape to 'long' format so Plotly can draw two bars side by side
        long = summary.melt(id_vars="Promotion", value_vars=["Avg. discount (%)", "Profit margin (%)"],
                            var_name="Measure", value_name="Percent")
        fig = px.bar(long, x="Promotion", y="Percent", color="Measure", barmode="group", text_auto=".1f",
                     color_discrete_map={"Avg. discount (%)": "#E0A526", "Profit margin (%)": "#2E9E5B"})
        fig.update_layout(xaxis_title=None, yaxis_title="%")
        st.plotly_chart(style(fig), key="chart_promo")


# ------------------------------------------------------ Customer profile
@st.fragment
def customer_card():
    data = get_global_data()
    with st.container(border=True):
        with card_header("Who is buying"):
            category = st.selectbox("Category", ["All categories"] + CATEGORIES, key="cust_category")
            loyalty = st.radio("Customers", ["All customers", "Loyalty members", "Non-members"], key="cust_loyalty")
            metric = st.radio("Measure", ["Net sales (AED)", "Transactions", "Average rating (1-5)"],
                              key="cust_metric")

        if category != "All categories":
            data = data[data["Category"] == category]
        if loyalty != "All customers":
            data = data[data["Loyalty_Member"] == ("Yes" if loyalty == "Loyalty members" else "No")]
        show_active_filters(category, loyalty, metric)
        if data.empty:
            return no_data_message()

        summary = summarise(data, ["Age_Group", "Gender"], metric)
        fig = px.bar(summary, x="Age_Group", y=metric, color="Gender", barmode="group",
                     text_auto=".2f" if metric.startswith("Average") else ".3s",
                     category_orders={"Age_Group": AGE_GROUPS},
                     color_discrete_map={"Female": "#ff4d5a", "Male": "#f2f2f7"},
                     labels={"Age_Group": "Age group"})
        st.plotly_chart(style(fig), key="chart_customers")


# ------------------------------------------------- Top sub-categories table
@st.fragment
def top_products_card():
    data = get_global_data()
    with st.container(border=True):
        with card_header("Top sub-categories"):
            chosen = st.multiselect("Categories", CATEGORIES, placeholder="All categories", key="top_categories")
            sort_by = st.selectbox("Rank by", ["Net sales (AED)", "Profit (AED)", "Units sold",
                                               "Transactions", "Profit margin (%)"], key="top_sort")
            top_n = st.slider("How many to show", 5, 30, 10, key="top_n")

        if chosen:
            data = data[data["Category"].isin(chosen)]
        show_active_filters(", ".join(chosen) if chosen else "All categories", f"top {top_n} by {sort_by}")
        if data.empty:
            return no_data_message()

        groups = data.groupby(["Sub_Category", "Category"])
        table = pd.DataFrame({
            "Net sales (AED)": groups["Net_Sales_AED"].sum(),
            "Profit (AED)": groups["Profit_AED"].sum(),
            "Units sold": groups["Units_Sold"].sum(),
            "Transactions": groups["Transaction_ID"].count(),
        })
        table["Profit margin (%)"] = table["Profit (AED)"] / table["Net sales (AED)"] * 100
        table = table.sort_values(sort_by, ascending=False).head(top_n).reset_index()

        st.dataframe(
            table, hide_index=True, height=CHART_HEIGHT,
            column_config={
                "Sub_Category": st.column_config.TextColumn("Sub-category", pinned=True),
                "Category": st.column_config.TextColumn(width="small"),
                # A bar inside the cell makes the biggest sellers easy to spot
                "Net sales (AED)": st.column_config.ProgressColumn(
                    "Net sales", format="compact", color="#2E9E5B", width="small",
                    min_value=0, max_value=float(table["Net sales (AED)"].max())),
                "Profit (AED)": st.column_config.NumberColumn("Profit", format="compact", width="small"),
                "Units sold": st.column_config.NumberColumn("Units", width="small"),
                "Transactions": st.column_config.NumberColumn("Txns", width="small"),
                "Profit margin (%)": st.column_config.NumberColumn("Margin", format="%.1f%%", width="small"),
            },
        )


# ------------------------------------------------------ Raw data explorer
@st.fragment
def data_explorer_card():
    data = get_global_data()
    all_columns = list(data.columns)
    starter_columns = ["Transaction_ID", "Timestamp", "Emirate", "Store_Name", "Category",
                       "Sub_Category", "Units_Sold", "Net_Sales_AED", "Profit_AED", "Promotion"]
    with st.container(border=True):
        with card_header("Raw data", wide=True):
            columns = st.multiselect("Columns to show", all_columns, default=starter_columns, key="raw_columns")
            category = st.selectbox("Category", ["All categories"] + CATEGORIES, key="raw_category")

        if category != "All categories":
            data = data[data["Category"] == category]
        columns = columns or all_columns          # nothing picked = show every column
        show_active_filters(category, f"{len(data):,} rows", f"{len(columns)} of {len(all_columns)} columns")

        st.dataframe(data[columns], hide_index=True, height=300)
        st.download_button("Download these rows as CSV", data[columns].to_csv(index=False),
                           file_name="lulu_sales_filtered.csv", mime="text/csv",
                           icon=":material/download:", on_click="ignore")


# =============================================================================
# 5b. NEW CARDS: insights, store leaderboard, store spotlight, time machine
# =============================================================================
@st.fragment
def insights_card():
    data = get_global_data()
    net = data["Net_Sales_AED"].sum()
    cat = data.groupby("Category")["Net_Sales_AED"].sum().sort_values(ascending=False)
    em = data.groupby("Emirate")["Net_Sales_AED"].sum().sort_values(ascending=False)
    store = data.groupby("Store_Name")["Net_Sales_AED"].sum().sort_values(ascending=False)
    month = data.groupby(data["Date"].dt.to_period("M"))["Net_Sales_AED"].sum()
    weekend = data.loc[data["Is_Weekend"] == "Yes", "Net_Sales_AED"].sum() / net * 100
    online = data.loc[data["Sales_Channel"] != "In-store", "Net_Sales_AED"].sum() / net * 100
    facts = [
        f"{cat.index[0]} leads with {cat.iloc[0] / net * 100:.0f}% of all sales.",
        f"{em.index[0]} is the top emirate, bringing in {aed(em.iloc[0])}.",
        f"{store.index[0]} is the star store with {aed(store.iloc[0])}.",
        f"{month.idxmax().strftime('%B %Y')} was the best month at {aed(month.max())}.",
        f"Weekends make up {weekend:.0f}% of sales. Online and click & collect make up {online:.0f}%.",
    ]
    st.session_state.setdefault("fact_i", 0)
    with st.container(border=True):
        text, b1, b2 = st.columns([5, 1.2, 1.4], vertical_alignment="center")
        text.markdown(f"### ✨ {facts[st.session_state['fact_i'] % len(facts)]}")
        b1.button("Surprise me", icon=":material/auto_awesome:", width="stretch",
                  on_click=lambda: st.session_state.update(fact_i=random.randrange(len(facts))))
        if b2.button("Best month!", icon=":material/celebration:", width="stretch"):
            st.balloons()
            st.toast(f"🎉 {month.idxmax().strftime('%B %Y')}: {aed(month.max())}")


@st.fragment
def store_leaderboard_card():
    data = get_global_data()
    with st.container(border=True):
        with card_header("Store leaderboard"):
            metric = st.radio("Measure", list(METRIC_COLUMNS), key="lb_metric")
            top_n = st.slider("Stores to show", 3, 17, 10, key="lb_n")
        show_active_filters(metric, f"top {top_n}")
        s = summarise(data, ["Store_Name", "Emirate"], metric).sort_values(metric, ascending=False).head(top_n)
        medals = ["🥇 ", "🥈 ", "🥉 "]
        s["Store"] = [(medals[i] if i < 3 else "") + n for i, n in enumerate(s["Store_Name"])]
        fig = px.bar(s, x=metric, y="Store", orientation="h", color="Emirate", text_auto=".3s")
        fig.update_yaxes(categoryorder="total ascending", title=None)
        st.plotly_chart(style(fig), key="chart_leaderboard")


@st.fragment
def store_spotlight_card():
    data = get_global_data()
    ranking = data.groupby("Store_Name")["Net_Sales_AED"].sum().sort_values(ascending=False)
    with st.container(border=True):
        st.markdown("#### 🔦 Store spotlight")
        store = local_select("Pick a store", sorted(ranking.index), key="spot_store")
        d = data[data["Store_Name"] == store]
        st.caption(f"📍 {store} · {d['Emirate'].iloc[0]} · {d['Store_Format'].iloc[0]} · "
                   f"rank #{list(ranking.index).index(store) + 1} of {len(ranking)} by net sales")
        a, b, c = st.columns(3)
        a.metric("Net sales", aed(d["Net_Sales_AED"].sum()))
        b.metric("Transactions", f"{len(d):,}")
        c.metric("Avg. rating", f"{d['Customer_Rating'].mean():.2f} ⭐")
        monthly = d.groupby(d["Date"].dt.to_period("M").dt.start_time)["Net_Sales_AED"].sum().reset_index()
        fig = px.area(monthly, x="Date", y="Net_Sales_AED", markers=True, color_discrete_sequence=["#ff4d5a"],
                      labels={"Net_Sales_AED": "Net sales (AED)", "Date": ""})
        st.plotly_chart(style(fig).update_layout(height=250), key="chart_spotlight")


@st.fragment
def time_machine_card():
    data = get_global_data()
    with st.container(border=True):
        with card_header("Time machine: press ▶ and watch sales move month by month", wide=True):
            by = st.radio("Race by", ["Category", "Emirate", "Store_Name"], key="tm_by",
                          format_func=lambda x: x.replace("_", " "))
            metric = st.radio("Measure", list(METRIC_COLUMNS), key="tm_metric")
        show_active_filters(by.replace("_", " "), metric)
        data = data.assign(Month=data["Date"].dt.strftime("%Y-%m"))
        s = summarise(data, [by, "Month"], metric).set_index([by, "Month"])[metric]
        full = pd.MultiIndex.from_product([sorted(data[by].unique()), sorted(data["Month"].unique())], names=[by, "Month"])
        s = s.reindex(full, fill_value=0).reset_index()
        fig = px.bar(s, x=metric, y=by, orientation="h", color=by, animation_frame="Month", text_auto=".3s",
                     range_x=[min(0, s[metric].min()), s[metric].max() * 1.15],
                     color_discrete_map=CATEGORY_COLORS if by == "Category" else None)
        fig.update_yaxes(categoryorder="total ascending", title=None)
        fig.update_layout(showlegend=False)
        if fig.layout.updatemenus:   # slow the play button down so the motion is easy to follow
            play = fig.layout.updatemenus[0].buttons[0].args[1]
            play["frame"]["duration"], play["transition"]["duration"] = 900, 600
        st.plotly_chart(style(fig).update_layout(height=520), key="chart_time_machine")


# =============================================================================
# 6. PAGES + LAYOUT
# =============================================================================
df = load_data()
first_day, last_day = df["Date"].min().date(), df["Date"].max().date()


def page_header(title, blurb):
    st.title(title)
    st.caption(blurb)


def overview_page():
    page_header("🌌 Overview", "The big picture. Slice everything with the filters in the sidebar.")
    insights_card()
    kpi_row()
    trend_card()
    sales_by_category_card()


def places_page():
    page_header("🗺️ Emirates & stores", "Where the sales happen: by emirate, by store, by location.")
    emirate_heatmap_card()
    left, right = st.columns(2)
    with left:
        store_leaderboard_card()
    with right:
        store_spotlight_card()


def time_page():
    page_header("⏳ Time machine", "Watch the year unfold. Press play, or drag the slider to a month.")
    time_machine_card()


def products_page():
    page_header("🛍️ Products & promotions", "What sells, and what discounts do to profit.")
    left, right = st.columns(2)
    with left:
        promotion_card()
    with right:
        top_products_card()


def customers_page():
    page_header("👥 Customers", "Who is buying, and how they shop and pay.")
    left, right = st.columns(2)
    with left:
        customer_card()
    with right:
        mix_card()


def data_page():
    page_header("📄 Data explorer", "Every transaction behind the charts. Download what you see.")
    data_explorer_card()


pg = st.navigation([
    st.Page(overview_page, title="Overview", icon="🌌", url_path="overview", default=True),
    st.Page(places_page, title="Emirates & stores", icon="🗺️", url_path="places"),
    st.Page(time_page, title="Time machine", icon="⏳", url_path="time-machine"),
    st.Page(products_page, title="Products & promos", icon="🛍️", url_path="products"),
    st.Page(customers_page, title="Customers", icon="👥", url_path="customers"),
    st.Page(data_page, title="Data explorer", icon="📄", url_path="data"),
])


def quick_range():
    days = {"Last 30 days": 30, "Last 90 days": 90}.get(st.session_state.get("quick"))
    st.session_state["global_dates"] = (first_day, last_day) if days is None else (
        max(first_day, last_day - timedelta(days=days - 1)), last_day)


def reset_filters():
    st.session_state.update(global_dates=(first_day, last_day), global_emirates=[], quick=None)


# ---- Global filters live in the sidebar so they follow you from page to page ----
with st.sidebar:
    st.markdown("### 🔭 Filters")
    st.date_input("Date range", value=(first_day, last_day), min_value=first_day,
                  max_value=last_day, format="DD/MM/YYYY", key="global_dates")
    st.segmented_control("Quick range", ["Last 30 days", "Last 90 days", "Full period"],
                         key="quick", on_change=quick_range)
    st.multiselect("Emirates", EMIRATES, placeholder="All emirates", key="global_emirates")
    st.button("Reset filters", icon=":material/restart_alt:", on_click=reset_filters, width="stretch")
    st.caption(f"Synthetic data for teaching. {len(df):,} transactions, "
               f"{first_day:%d %b %Y} to {last_day:%d %b %Y}.")

if "welcomed" not in st.session_state:
    st.session_state["welcomed"] = True
    st.toast("Welcome, stargazer! Try the Time machine page ✨")

if len(st.session_state["global_dates"]) != 2:
    st.info("Pick an end date to finish setting the date range.")
    st.stop()
if get_global_data().empty:
    st.warning("No transactions in this date range and emirate selection. Widen the filters in the sidebar.")
    st.stop()

pg.run()
