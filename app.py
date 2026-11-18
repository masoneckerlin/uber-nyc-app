"""
Mason Eckerlin
CS 230 - 7 
Data: Uber Pickups in New York City, April 2014 
Source: FiveThirtyEight, Uber TLC FOIL Response (github.com/fivethirtyeight/uber-tlc-foil-response)
LLM used: Claude

This program/app will be used to help an Uber driver in Manhattan who can only drive a few shifts a week, and wants to know what days, areas, and hours produce the most pickups. 
"""

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import pydeck as pdk

DATA_FILE = 'uber_nyc_pickups_april2014_sample.csv'

# Base license codes from the GitHub link
BASE_NAMES = {
    "B02512": "Unter",
    "B02598": "Hinter",
    "B02617": "Weiter",
    "B02682": "Schmecken",
    "B02764": "Danach-NY",
}

# Base name line colors for Q3 chart
BASE_COLORS = {
    "Unter": "steelblue",
    "Hinter": "darkorange",
    "Weiter": "seagreen",
    "Schmecken": "crimson",
    "Danach-NY": "purple",
}

# Rough box-outline around the five NYC boroughs where ~ all pickups took place
NYC_LAT = (40.47, 40.92)
NYC_LON = (-74.26, -73.70)


#[DICT_DRIVEN] AUGMENT
# This dictionary controls the dropdown for question 2, the keys are the choices the user sees, and the values
# are the days that the choices filter to.
# I added an "All days" so if a driver drives every day of the week, they can view the full week.
# The dropdown is built from DAY_GROUPS.keys(), so all I had to add was the one line
# Above, BASE_NAMES/COLORS work the same way, where base codes are turned into names and are assigned a color for
# the dropdown in question 3
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_GROUPS = {
    "Weekdays (Mon-Fri)": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "Weekend (Sat-Sun)": ["Saturday", "Sunday"],
    "All days (Mon-Sun)": DAY_ORDER,
}

st.title("Where and When to Drive: Uber Pickups in NYC, April 2014")

#[INPUT_CHECK] REVISE/REWRITE
# AI's version returned (df, note), and I simplified the code to return only df, or None if the file is missing
# I moved the error message to st.error at the bottom of the app
# try/except catches a missing file instead of crashing, errors='coerce' turns bad dates into NaT so they are dropped
# There are also if checks in each of the three questions that show a warning when no days or bases are chosen, or 
# when no pickups match
@st.cache_data
def load_data(path):
    # read the CSV, return None
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        return None

    # convert date & time from text into dates, use 'coerce' to 
    # turn values that won't convert into NaT instead of crashing
    df["Date/Time"] = pd.to_datetime(df["Date/Time"], format = "%m/%d/%Y %H:%M:%S", errors = "coerce")
    df = df.dropna(subset = ["Date/Time"])

    # build new columns from cleaned dates, hour of day, days of week
    df["hour"] = df["Date/Time"].dt.hour
    df["day"] = df["Date/Time"].dt.day_name()
    df["date"] = df["Date/Time"].dt.date

    # keep pickups only in NYC, exclude the few outside of the LAT/LON constants
    in_nyc = df["Lat"].between(NYC_LAT[0], NYC_LAT[1]) & df["Lon"].between(NYC_LON[0], NYC_LON[1])
    df = df[in_nyc].copy()

    # use only readable base names; unknowns keep their original code
    df["base_name"] = df["Base"].map(BASE_NAMES).fillna(df["Base"])

    return df

def count_by_hour_loop(hours):
    # count pickups per hour with a loop and dictionary in every row
    counts = {}
    for h in hours:
        counts[h] = counts.get(h, 0) + 1
    return counts

#[AI_REWRITE] REVISE/REWRITE
# AI's version: matches = all(loop_counts[h] == pandas_counts[h] for h in pandas_counts.index)
# I rewrote this to be a function when a plain for loop with an if statement, so each step is on its own
# line with a comment. It is easier for me to read and debug, the loop stops at the first mismatch
def counts_match(loop_counts, pandas_counts):
    # check every hour that Pandas counted
    for h in pandas_counts.index:
        # if the loop's count for this hour is different, the two methods don't agree
        if loop_counts[h] != pandas_counts[h]:
            return False
    # if no differences found, every hour matched, so return True
    return True

def question1(df):
    st.header("1. When are pickups busiest?")
    st.write("Pick the days you can drive and the hours you are available.")

    # allows for a user to select multiple days and then a list is created
    days = st.multiselect("Days you can drive", DAY_ORDER, default=["Friday", "Saturday"])
    start, end = st.slider("Hours you are available (24-hour clock)", 0, 23, (15, 22))

    # check the inputs before analysis
    if not days:
        st.warning("Choose at least one day to see results")
        return

    # capture all pickups on the chosen days and inside of the chosen hours
    day_df = df[df["day"].isin(days)]
    window = day_df[day_df["hour"].between(start, end)]

    if window.empty:
        st.warning("No pickups in this sample match these days and hours. Try a wider hour range.")
        return


    #[LOOP_VS_PANDAS] IDENTIFY & EXPLAIN
    # AI wrote this to count the pickups per hour in the chosen window
    # count_by_hour_loop goes through every pickup's hour and adds 1 to that hour in a dictionary. 
    # groupby("hour").size does the same count in Pandas
    # counts_ match then confirms both give the same result, which is shown in the caption
    # Example: hours [19, 19, 20], the loop gives {19: 2, 20: 1}, Pandas gives 19: 2, 20: 1 (matching)
    # Result: Friday + Saturday, 15-22, both loop and pandas give 78 pickups at 19:00, match = True
    # pickups per hour in the chosen window
    loop_counts = count_by_hour_loop(window["hour"])
    pandas_counts = window.groupby("hour").size()
    # make sure Pandas and loop agree
    matches = counts_match(loop_counts, pandas_counts)

    # fill in hours with zero pickups so every hour has a bar on the graph
    hours = list(range(start, end + 1))
    counts = [int(pandas_counts.get(h, 0)) for h in hours]

    # average pickups per hour across the entire day on the chosen days
    day_avg = len(day_df) / 24

    # highlight peak hour in red, rest in blue
    peak_hour = hours[counts.index(max(counts))]
    colors = ["red" if h == peak_hour else "steelblue" for h in hours]

    fig, ax = plt.subplots()
    ax.bar(hours, counts, color=colors)
    # num of pickups a typical hour gets on the days that the user picks, if pickups were evenly spread throughout the day
    ax.axhline(day_avg, color="gray", linestyle="--", label="Average per hour (all 24 hours)")
    ax.set_title("Pickups by Hour")
    ax.set_xlabel("Hour of day (24-hour clock)")
    ax.set_ylabel("Number of pickups")
    ax.set_xticks(hours)
    # AI's version used only max(counts, which hid the average line on slow hours. I changed it to fit whatever it taller
    # the bars or the average
    ax.set_ylim(0, max(max(counts), day_avg) * 1.25) # add extra height to chart's y-axis
    ax.legend()
    st.pyplot(fig)

    # Which chosen day has the most pickups in the user input hours
    by_day = window.groupby("day").size().sort_values(ascending=False)
    by_day.index.name = "Day"
    st.write("**Your chosen days, ranked by pickups in your hours:**")
    st.dataframe(by_day.rename("Pickups"))

    # display the confirmation that the loop and the pandas show the same result
    st.caption(f"Check: loop count and Pandas groupby count match: {matches}")

def question2(df):
    st.header("2. Where are pickups concentrated?")
    st.write("Choose weekdays or weekends and a time window. Brighter areas on the map had more pickups.")

    # user inputs with dropdown for weekdays/ends, range slider for hours
    day_type = st.selectbox("Show pickups for", list(DAY_GROUPS.keys()))
    start, end = st.slider("Hours (24-hour clock)", 0, 23, (17, 20))

    # filter with conditions of chosen day group and chosen hours
    days = DAY_GROUPS[day_type]
    chosen = df[df["day"].isin(days) & df["hour"].between(start, end)]

    if chosen.empty:
        st.warning("No pickups match this time window. Try a wider hour range.")
        return

    # heatmap layer, areas are shaded by how many pickups are close together
    # I chose a heatmap over individual points because it didn't make sense to me, or seem likely that a 
    # driver would be looking at individual data points for pickups
    heat_layer = pdk.Layer(
        "HeatmapLayer",
        data = chosen[["Lat", "Lon"]],
        get_position=["Lon", "Lat"],
        radius_pixels = 40,
    )

    # start the map centered in Manhattan area, coordinates found on Google
    view = pdk.ViewState(latitude=40.75, longitude=-74, zoom=11)

    st.pydeck_chart(pdk.Deck(layers=[heat_layer], initial_view_state=view))
    st.write(f"**{len(chosen)}** pickups on {day_type.lower()} between {start}:00 and {end}:59.")

def question3(df):
    st.header("3. Which bases handled the most pickups?")
    st.write("Choose bases and dates to compare how many pickups each Uber base handled.")

    # user inputs, which bases/dates
    bases = st.multiselect("Uber bases", list(BASE_COLORS.keys()), default=list(BASE_COLORS.keys()))
    dates = st.date_input("Date range", value=(df["date"].min(), df["date"].max()))

    # check inputs before analysis
    if not bases:
        st.warning("Choose at least one base to see results.")
        return
    if len(dates) != 2:
        st.info("Pick an end date to finish the date range.")
        return

    # filter to the selected date range, and then the chosen Uber bases
    in_range = df[df["date"].between(dates[0], dates[1])]
    chosen = in_range[in_range["base_name"].isin(bases)]

    if chosen.empty:
        st.warning("No pickups for these bases in this date range.")
        return

    # count pickups for each date and base, with one column per base
    daily = chosen.groupby(["date", "base_name"]).size().unstack(fill_value=0)

    fig, ax = plt.subplots()
    for base in daily.columns:
        ax.plot(daily.index, daily[base], label = base, color=BASE_COLORS[base])
    ax.set_title("Daily Pickups by Uber Base")
    ax.set_xlabel("Date")
    ax.set_ylabel("Number of pickups")
    ax.legend(title="Base", loc="upper left", bbox_to_anchor=(1, 1))
    fig.autofmt_xdate()
    st.pyplot(fig)

    # total pickups and % share of all pickups in the chosen date range
    summary = chosen.groupby("base_name").size().to_frame("Pickups")
    # divide by all pickups in the date range, not just the chosen bases
    # so each base's % is out of the whole list
    summary["Share %"] = (summary["Pickups"] / len(in_range) * 100).round(1)
    st.dataframe(summary.sort_values("Pickups", ascending=False))

    st.caption("Caution: a base with more pickups likely had more drivers, so a bigger share does not mean each driver at that base was busier.")

df = load_data(DATA_FILE)

if df is None:
    st.error(f"Could not find {DATA_FILE}. Make sure it is in the same folder as app.py.")
    st.stop()

# sidebar navigation, each page will answer one of the designated questions
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["1. Busiest hours", "2. Pickup hot spots", "3. Uber bases"])
st.sidebar.caption(f"{len(df):,} NYC pickups loaded from the April 2014 sample.")
st.sidebar.caption("Caution: this is a 3,000-pickup sample of one month, so small hour ranges can have very few pickups. Counts show demand, not how many drivers were competing.")

if page == "1. Busiest hours":
    question1(df)
elif page == "2. Pickup hot spots":
    question2(df)
else:
    question3(df)