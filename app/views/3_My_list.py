"""The companies I saved, with a note on each, and a CSV to take away."""
from urllib.parse import quote_plus

import streamlit as st

from common import get_connection, lei, show_data_note, show_status
from shortlist import get_list, list_as_csv, remove_from_list, update_note

st.title("My list")
conn = get_connection()
rows = get_list(conn)

if not rows:
    st.info("Nothing saved yet. Pick a company on Explore and add it here.")
else:
    # Excel needs the signature at the start of the file to read diacritics correctly.
    st.download_button(
        "Download as CSV",
        list_as_csv(rows).encode("utf-8-sig"),
        file_name="my_list.csv",
        mime="text/csv",
    )
    for row in rows:
        with st.container(border=True):
            if row["in_data"]:
                st.subheader(row["name"])
                show_status(row["status_group"])
                st.write(
                    f"{row['county'] or 'County not given'}, {row['category'] or 'not an IT category'}. "
                    f"Latest accounts: {row['latest_year'] or 'none'}, revenue {lei(row['revenue'])}."
                )
                search = quote_plus(f"{row['name']} cariere")
                st.link_button("Search for its careers page", f"https://www.google.com/search?q={search}")
            else:
                st.subheader(f"CUI {row['cui']}")
                st.warning("This company isn't in the currently loaded data.")

            note = st.text_area("Note", row["note"] or "", key=f"note-{row['cui']}")
            with st.container(horizontal=True):
                if st.button("Save note", key=f"save-{row['cui']}"):
                    update_note(conn, row["cui"], note)
                    st.rerun()
                if st.button("Remove from list", key=f"remove-{row['cui']}"):
                    remove_from_list(conn, row["cui"])
                    st.rerun()

show_data_note()
