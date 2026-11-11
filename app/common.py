"""What every page shares: the database connection and the note about the data."""
import os

import psycopg
import streamlit as st

STATUS_LABELS = {
    "active": "Active",
    "suspended": "Suspended",
    "insolvency": "Insolvency",
    "dissolution_liquidation": "Dissolution or liquidation",
    "bankruptcy": "Bankruptcy",
    "deregistered": "Deregistered",
    "unknown": "Unknown",
}
STATUS_COLORS = {
    "active": "green",
    "suspended": "orange",
    "insolvency": "orange",
    "dissolution_liquidation": "red",
    "bankruptcy": "red",
}
# County: its licence plate code, then column and row on a grid that roughly follows the map.
COUNTY_TILES = {
    "Satu Mare": ("SM", 2, 0), "Maramureș": ("MM", 3, 0), "Suceava": ("SV", 5, 0), "Botoșani": ("BT", 6, 0),
    "Bihor": ("BH", 2, 1), "Sălaj": ("SJ", 3, 1), "Bistrița-Năsăud": ("BN", 4, 1), "Neamț": ("NT", 5, 1),
    "Iași": ("IS", 6, 1),
    "Arad": ("AR", 2, 2), "Cluj": ("CJ", 3, 2), "Mureș": ("MS", 4, 2), "Harghita": ("HR", 5, 2),
    "Bacău": ("BC", 6, 2), "Vaslui": ("VS", 7, 2),
    "Timiș": ("TM", 2, 3), "Alba": ("AB", 3, 3), "Sibiu": ("SB", 4, 3), "Brașov": ("BV", 5, 3),
    "Covasna": ("CV", 6, 3), "Vrancea": ("VN", 7, 3), "Galați": ("GL", 8, 3),
    "Caraș-Severin": ("CS", 2, 4), "Hunedoara": ("HD", 3, 4), "Vâlcea": ("VL", 4, 4), "Argeș": ("AG", 5, 4),
    "Prahova": ("PH", 6, 4), "Buzău": ("BZ", 7, 4), "Brăila": ("BR", 8, 4), "Tulcea": ("TL", 9, 4),
    "Mehedinți": ("MH", 2, 5), "Gorj": ("GJ", 3, 5), "Olt": ("OT", 4, 5), "Dâmbovița": ("DB", 5, 5),
    "București": ("B", 6, 5), "Ialomița": ("IL", 7, 5), "Călărași": ("CL", 8, 5), "Constanța": ("CT", 9, 5),
    "Dolj": ("DJ", 3, 6), "Teleorman": ("TR", 4, 6), "Ilfov": ("IF", 5, 6), "Giurgiu": ("GR", 6, 6),
}


@st.cache_resource
def get_connection():
    return psycopg.connect(
        host="db",
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        autocommit=True,
    )


def show_status(status_group):
    st.badge(STATUS_LABELS.get(status_group, status_group), color=STATUS_COLORS.get(status_group, "gray"))


def lei(amount):
    return "not reported" if amount is None else f"{amount:,.0f} lei"


def show_data_note():
    st.caption(
        "Sources: Trade Registry (ONRC, snapshot 2026-11-04) and Ministry of Finance accounts, "
        "from data.gov.ro, CC BY 4.0. Amounts in lei, not adjusted for inflation. "
        "2025 may still be incomplete. These numbers say nothing about jobs, salaries or culture."
    )
