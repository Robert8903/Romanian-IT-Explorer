"""Where the app starts: the page settings and the navigation bar."""
import streamlit as st

st.set_page_config(page_title="Romanian IT Career Explorer", layout="wide")

st.navigation(
    [
        st.Page("views/0_Map.py", title="Map", default=True),
        st.Page("views/1_Explore.py", title="Explore"),
        st.Page("views/2_Compare.py", title="Compare"),
        st.Page("views/3_My_list.py", title="My list"),
    ],
    position="top",
).run()
