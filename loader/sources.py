"""The exact files we download from data.gov.ro, and how many rows each one has."""

BASE = "https://data.gov.ro/dataset"

REGISTRY_SNAPSHOT = "2026-11-04"

REGISTRY = {
    "firms": {
        "url": f"{BASE}/c2c88c9d-4824-45f1-90ec-656f1c0d8785/resource/869eac01-8480-4ac6-a18d-d0f044b0db80/download/od_firme.csv",
        "expected_rows": 4233074,
    },
    "statuses": {
        "url": f"{BASE}/c2c88c9d-4824-45f1-90ec-656f1c0d8785/resource/6cf3a51a-aac2-42e5-aee1-41326b3a9aaa/download/od_stare_firma.csv",
        "expected_rows": 4676946,
    },
    "status_codes": {
        "url": f"{BASE}/238b4f02-19a5-446d-b4dc-780c4f3e88aa/resource/90bb0080-6caf-4cda-88e3-25e01681648b/download/n_stare_firma.csv",
        "expected_rows": 197,
    },
}

ACCOUNTS = {
    2021: {
        "abbreviated": {
            "url": f"{BASE}/f8353c0e-fee9-4aa3-b26d-be0e96c328a7/resource/d9411926-c66d-4b27-a28c-7b590425efd3/download/web_uu_an2021.txt",
            "expected_rows": 709662,
        },
        "long": {
            "url": f"{BASE}/f8353c0e-fee9-4aa3-b26d-be0e96c328a7/resource/d0a42232-5aa0-425a-b264-67184e8ded5f/download/web_bl_bs_sl_an2021.txt",
            "expected_rows": 71808,
        },
        "ifrs": {
            "url": f"{BASE}/f8353c0e-fee9-4aa3-b26d-be0e96c328a7/resource/15e36a41-ac3d-4494-a506-be122a2ace4d/download/web_ir_an2021.txt",
            "expected_rows": 108,
        },
    },
    2022: {
        "abbreviated": {
            "url": f"{BASE}/aa2567a4-e7d7-4e6e-ab19-d08d39f99996/resource/7f31544a-1f85-4700-8fe6-9cd19fcf8515/download/web_uu_an2022.txt",
            "expected_rows": 785925,
        },
        "long": {
            "url": f"{BASE}/aa2567a4-e7d7-4e6e-ab19-d08d39f99996/resource/b35fab04-f101-42d7-a765-8f41728b373a/download/web_bl_bs_sl_an2022.txt",
            "expected_rows": 76639,
        },
        "ifrs": {
            "url": f"{BASE}/aa2567a4-e7d7-4e6e-ab19-d08d39f99996/resource/f1c5217b-2204-4961-8264-f07ab55e3f2d/download/web_ir_an2022.txt",
            "expected_rows": 99,
        },
    },
    # 2023 has two versions of each file on the portal: these are the "actualizat" ones.
    2023: {
        "abbreviated": {
            "url": f"{BASE}/7861a98f-4d5c-4faa-90d4-8e934ebd1782/resource/ee5b6665-c096-4582-ada7-cc51a62c3c40/download/web_uu_an2023.txt",
            "expected_rows": 860374,
        },
        "long": {
            "url": f"{BASE}/7861a98f-4d5c-4faa-90d4-8e934ebd1782/resource/8c914899-cf2a-494c-9d3b-7f9f7faa47a3/download/web_bl_bs_sl_an2023.txt",
            "expected_rows": 84173,
        },
        "ifrs": {
            "url": f"{BASE}/7861a98f-4d5c-4faa-90d4-8e934ebd1782/resource/2284ec52-40a9-4f01-8a01-9a93484e43b3/download/web_ir_an2023.txt",
            "expected_rows": 108,
        },
    },
    # From the set "Situatii financiare 2024 actualizat iunie 2026".
    2024: {
        "abbreviated": {
            "url": f"{BASE}/cc8de892-f661-4f6e-97c0-15f5271d8a13/resource/d5f28351-4663-4001-94ea-fced080650c7/download/web_uu_an2024.txt",
            "expected_rows": 885106,
        },
        "long": {
            "url": f"{BASE}/cc8de892-f661-4f6e-97c0-15f5271d8a13/resource/697376d1-c958-48a6-ab87-ca006636780b/download/web_bl_bs_sl_an2024.txt",
            "expected_rows": 83488,
        },
        "ifrs": {
            "url": f"{BASE}/cc8de892-f661-4f6e-97c0-15f5271d8a13/resource/19c83864-165a-4386-a8f7-c3269a7784c4/download/web_ir_an2024.txt",
            "expected_rows": 110,
        },
    },
    2025: {
        "abbreviated": {
            "url": f"{BASE}/e2266fdc-0a6b-43b8-9c9f-7a6943d85b28/resource/eeecc692-d914-4d3b-b7f5-d1a8a9791979/download/web_uu_an2025.txt",
            "expected_rows": 844207,
        },
        "long": {
            "url": f"{BASE}/e2266fdc-0a6b-43b8-9c9f-7a6943d85b28/resource/3540a9ce-6a4d-4e29-9aa1-ac909fe28ac1/download/web_bl_bs_sl_an2025.txt",
            "expected_rows": 74025,
        },
        "ifrs": {
            "url": f"{BASE}/e2266fdc-0a6b-43b8-9c9f-7a6943d85b28/resource/38a8cc80-3470-49a0-9335-7ae020d8239d/download/web_ir_an2025.txt",
            "expected_rows": 102,
        },
    },
}
