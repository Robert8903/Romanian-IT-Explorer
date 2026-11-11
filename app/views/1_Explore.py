"""Search and filter companies, then look closer at one of them."""
import pandas as pd
import streamlit as st

from common import STATUS_LABELS, get_connection, lei, show_data_note, show_status
from queries import DEFAULT_IT_CATEGORIES, Filters, company_statuses, filter_options, search_companies
from shortlist import add_to_list

LIMIT = 200

st.title("Explore")
conn = get_connection()


@st.cache_data
def load_options():
    return filter_options(conn)


options = load_options()

with st.container(border=True):
    name_column, employees_column, revenue_column = st.columns([2, 1, 1])
    name = name_column.text_input("Company name", placeholder="Part of the legal name")
    min_employees = employees_column.number_input("At least this many employees", min_value=0, value=1, step=1)
    min_revenue = revenue_column.number_input("At least this revenue (lei)", min_value=0, value=0, step=100000)

    activity_column, status_column, county_column = st.columns([2, 1, 1])
    categories = activity_column.multiselect(
        "Activity (empty = all companies)", options["categories"], default=DEFAULT_IT_CATEGORIES
    )
    statuses = status_column.multiselect(
        "Status (empty = all)",
        options["statuses"],
        default=["active"],
        format_func=lambda status: STATUS_LABELS.get(status, status),
    )
    # The key lets a click on the map arrive here with its county already chosen.
    counties = county_column.multiselect("County (empty = all)", options["counties"], key="explore_counties")

filters = Filters(
    name=name,
    counties=counties,
    categories=categories,
    statuses=statuses,
    min_employees=min_employees or None,
    min_revenue=min_revenue or None,
)
rows = search_companies(conn, filters, limit=LIMIT)

if not rows:
    st.info("No companies match these filters.")
else:
    if len(rows) == LIMIT:
        st.caption(f"Showing the first {LIMIT}, sorted by employees. Narrow the filters to see others.")
    table = pd.DataFrame(
        {
            "Name": [row["name"] for row in rows],
            "County": [row["county"] for row in rows],
            "Category": [row["category"] for row in rows],
            "Status": [STATUS_LABELS.get(row["status_group"], row["status_group"]) for row in rows],
            "Latest year": [row["latest_year"] for row in rows],
            "Employees": [row["employees"] for row in rows],
            "Revenue (lei)": [row["revenue"] for row in rows],
            "Net result (lei)": [row["net_result"] for row in rows],
            "Revenue per employee (lei)": [row["revenue_per_employee"] for row in rows],
            "Revenue change (%)": [row["revenue_change_pct"] for row in rows],
            "Change period": [row["period"] for row in rows],
        }
    )
    for column in ["Employees", "Revenue (lei)", "Net result (lei)", "Revenue per employee (lei)", "Revenue change (%)"]:
        table[column] = pd.to_numeric(table[column])

    number = st.column_config.NumberColumn(format="localized")
    selection = st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        on_select="rerun",
        selection_mode="single-row",
        # New filters mean a new table, so an old selection can't point at the wrong company.
        key=f"results-{filters}",
        column_config={
            "Latest year": st.column_config.NumberColumn(format="%d"),
            "Employees": number,
            "Revenue (lei)": number,
            "Net result (lei)": number,
            "Revenue per employee (lei)": st.column_config.NumberColumn(format="localized", step=1),
            "Revenue change (%)": st.column_config.NumberColumn(format="%.1f"),
        },
    )

    selected = selection.selection.rows
    if selected:
        company = rows[selected[0]]
        with st.container(border=True):
            st.subheader(company["name"])
            show_status(company["status_group"])
            st.write(f"CUI {company['cui']}, {company['locality'] or 'locality not given'}, {company['county'] or 'county not given'}")
            employees, revenue, net_result = st.columns(3)
            employees.metric("Employees", "not reported" if company["employees"] is None else f"{company['employees']:,.0f}")
            revenue.metric(f"Revenue, {company['latest_year'] or 'no year'}", lei(company["revenue"]))
            net_result.metric(f"Net result, {company['latest_year'] or 'no year'}", lei(company["net_result"]))
            if company["employees_suspect"]:
                st.warning("The reported number of employees looks wrong, so it's left out. Worth checking.")
            statuses_found = company_statuses(conn, company["cui"])
            st.write("Registry statuses: " + (", ".join(statuses_found) if statuses_found else "none recorded"))
            if st.button("Add to My list"):
                add_to_list(conn, company["cui"])
                st.success("Added to My list.")

show_data_note()
