"""Up to 5 companies on the same years. A missing year stays a gap, never a zero."""
import altair as alt
import pandas as pd
import streamlit as st

from common import get_connection, show_data_note
from queries import Filters, company_history, search_companies

MAX_COMPANIES = 5

st.title("Compare")
conn = get_connection()
chosen = st.session_state.setdefault("compare", {})

text = st.text_input("Find a company to add")
if text.strip():
    found = search_companies(conn, Filters(name=text, categories=[], statuses=[], min_employees=None), limit=20)
    if not found:
        st.info("No company with that name.")
    else:
        pick = st.selectbox(
            "Matches, largest first",
            found,
            format_func=lambda row: f"{row['name']} ({row['county'] or 'no county'}, CUI {row['cui']})",
        )
        full = len(chosen) >= MAX_COMPANIES
        if st.button("Add", disabled=full, help=f"Up to {MAX_COMPANIES} companies" if full else None):
            chosen[pick["cui"]] = pick["name"]
            st.rerun()

if chosen:
    with st.container(horizontal=True):
        for cui, name in list(chosen.items()):
            if st.button(name, key=f"remove-{cui}", icon=":material/close:", help="Remove from the comparison"):
                del chosen[cui]
                st.rerun()

if len(chosen) < 2:
    st.info("Add at least two companies to compare them.")
else:
    history = pd.DataFrame(company_history(conn, list(chosen)))
    # Companies that share a name stay separate lines.
    history["Company"] = history["cui"].map(lambda cui: f"{chosen[cui]} ({cui})")
    for column in ["revenue", "net_result", "employees"]:
        history[column] = pd.to_numeric(history[column])

    for chart_column, (column, title) in zip(
        st.columns(3),
        [
            ("revenue", "Revenue (lei)"),
            ("net_result", "Net result (lei)"),
            ("employees", "Employees"),
        ],
    ):
        chart = (
            alt.Chart(history)
            .mark_line(point=True, strokeWidth=3)
            .encode(
                x=alt.X("year:O", title="Year", axis=alt.Axis(labelAngle=0)),
                y=alt.Y(f"{column}:Q", title=title),
                color=alt.Color("Company:N", legend=alt.Legend(orient="bottom", columns=1, title=None, labelLimit=320)),
                tooltip=["Company", "year", column],
            )
        )
        chart_column.altair_chart(chart, width="stretch")

    for company, rows in history.groupby("Company"):
        missing = rows.loc[rows["revenue"].isna() & rows["net_result"].isna() & rows["employees"].isna(), "year"]
        if len(missing):
            years = ", ".join(str(year) for year in missing)
            st.warning(f"{company} has no accounts for {years}.")
    if history["employees_suspect"].any():
        st.warning("Employee numbers that look wrong are left out of the chart.")

show_data_note()
