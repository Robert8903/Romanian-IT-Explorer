"""Start page: how many IT employers each county has. A click opens that county on Explore."""
import altair as alt
import pandas as pd
import streamlit as st

from common import COUNTY_TILES, get_connection, show_data_note
from queries import it_companies_by_county

BACKGROUND = "#1B1560"
LIGHT_TEXT = "#F4F1FF"
# From this many companies a tile is bright enough to need dark text.
DARK_TEXT_FROM = 1000

conn = get_connection()
counts = it_companies_by_county(conn)
companies = conn.execute("SELECT count(*) FROM company_profile").fetchone()[0]
years = conn.execute("SELECT min(year), max(year) FROM financials").fetchone()

st.title("Where in Romania could you work in IT?")
st.write(
    f"{sum(counts.values()):,} active IT companies with at least one employee, "
    "counted at their registered office."
)

tiles = pd.DataFrame(
    [
        {"County": county, "Plate": plate, "column": column, "row": row, "Companies": counts.get(county, 0)}
        for county, (plate, column, row) in COUNTY_TILES.items()
    ]
)
tiles["Ink"] = tiles["Companies"].map(lambda count: BACKGROUND if count >= DARK_TEXT_FROM else LIGHT_TEXT)

picked_county = alt.selection_point(name="county_pick", fields=["County"])
base = alt.Chart(tiles).encode(x=alt.X("column:O", axis=None), y=alt.Y("row:O", axis=None))
tile = (
    base.mark_rect(cornerRadius=4, stroke=BACKGROUND, strokeWidth=3, cursor="pointer")
    .encode(
        # A log scale, otherwise București would leave every other county the same colour.
        color=alt.Color(
            "Companies:Q",
            scale=alt.Scale(type="symlog", range=["#3A2FA6", "#C4469A", "#FFC93C"]),
            legend=None,
        ),
        tooltip=["County", alt.Tooltip("Companies:Q", format=",")],
    )
    .add_params(picked_county)
)
plate = base.mark_text(fontSize=19, fontWeight=800, dy=-8).encode(text="Plate:N", color=alt.Color("Ink:N", scale=None))
count = base.mark_text(fontSize=12, dy=12).encode(
    text=alt.Text("Companies:Q", format=","), color=alt.Color("Ink:N", scale=None)
)
chart = (tile + plate + count).resolve_scale(color="independent").properties(height=540).configure_view(stroke=None)

map_side, links_side = st.columns([3, 1], gap="large")
with map_side:
    event = st.altair_chart(chart, width="stretch", on_select="rerun", selection_mode="county_pick", key="county_map")
    if event.selection.county_pick:
        st.session_state["explore_counties"] = [event.selection.county_pick[0]["County"]]
        st.switch_page("views/1_Explore.py")

with links_side:
    st.subheader("Click a county to see its companies")
    st.caption(
        f"The database holds {companies:,} companies"
        + (f" and their accounts for {years[0]}–{years[1]}." if years[0] else ".")
    )

show_data_note()
