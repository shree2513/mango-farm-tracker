"""
Mango Farm Tree Tracker
=======================
Mobile-friendly Streamlit app for logging 200 mango trees.
Uses gspread to write directly to Google Sheets.
Photos are uploaded to Google Drive.
"""

import io
import streamlit as st
import pandas as pd
import gspread
from datetime import date
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


# ══════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Mango Farm Tracker 🥭",
    page_icon="🥭",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ══════════════════════════════════════════════════════════
# MOBILE-FRIENDLY CSS
# ══════════════════════════════════════════════════════════
st.markdown("""
<style>
    html, body, [class*="css"] { font-size: 17px; }

    label, .stRadio > label > div,
    .stSelectbox > label, .stTextInput > label,
    .stTextArea > label, .stDateInput > label,
    .stFileUploader > label {
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        color: #1b4332 !important;
    }

    .stRadio div[role="radiogroup"] label {
        font-size: 1.15rem !important;
        padding: 6px 0;
    }

    div.stButton > button:first-child {
        background-color: #1b4332;
        color: #ffffff;
        font-size: 1.35rem !important;
        font-weight: 800 !important;
        height: 3.8rem;
        width: 100%;
        border-radius: 14px;
        border: none;
        margin-top: 12px;
    }
    div.stButton > button:first-child:hover {
        background-color: #2d6a4f;
        color: #ffffff;
    }

    input, textarea, select {
        font-size: 1.05rem !important;
        padding: 10px !important;
    }

    h1 { color: #1b4332 !important; text-align: center; }
    h3 { color: #2d6a4f !important; }
    hr { border-color: #b7e4c7; margin: 1.2rem 0; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
# GOOGLE CREDENTIALS HELPER
# ══════════════════════════════════════════════════════════

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def get_credentials():
    """Build service account credentials from Streamlit secrets."""
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES,
    )


# ══════════════════════════════════════════════════════════
# GOOGLE SHEETS HELPER
# ══════════════════════════════════════════════════════════

def append_row_to_sheet(row_data: list):
    """
    Appends a single row to the TreeLog worksheet.
    row_data must be a list matching the column order in your sheet.
    """
    creds = get_credentials()
    client = gspread.authorize(creds)

    sheet_id = st.secrets["spreadsheet_id"]
    spreadsheet = client.open_by_key(sheet_id)
    worksheet = spreadsheet.worksheet("TreeLog")

    worksheet.append_row(row_data, value_input_option="USER_ENTERED")


# ══════════════════════════════════════════════════════════
# GOOGLE DRIVE PHOTO UPLOAD
# ══════════════════════════════════════════════════════════

def upload_photo_to_drive(photo_bytes: bytes, filename: str) -> str:
    """
    Uploads a photo to the Google Drive folder in secrets.
    Returns a shareable view URL.
    """
    creds = get_credentials()
    drive = build("drive", "v3", credentials=creds)

    folder_id = st.secrets["drive_folder_id"]

    file_metadata = {
        "name": filename,
        "parents": [folder_id],
    }
    media = MediaIoBaseUpload(
        io.BytesIO(photo_bytes),
        mimetype="image/jpeg",
        resumable=False,
    )
    uploaded = drive.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    file_id = uploaded.get("id")

    # Make publicly viewable
    drive.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()

    return f"https://drive.google.com/file/d/{file_id}/view"


# ══════════════════════════════════════════════════════════
# APP HEADER
# ══════════════════════════════════════════════════════════

st.title("🥭 Mango Farm Tracker")
st.markdown("### Log a Tree Update")
st.caption("Fill in the details below and tap **Save Update**.")
st.divider()


# ══════════════════════════════════════════════════════════
# DATA ENTRY FORM
# ══════════════════════════════════════════════════════════

with st.form("tree_log_form", clear_on_submit=True):

    tree_number = st.selectbox(
        "🌳 Tree Number",
        options=list(range(1, 201)),
        index=0,
        help="Select the number on the tree tag.",
    )

    log_date = st.date_input("📅 Date of Update", value=date.today())

    st.divider()

    st.markdown("**🩺 Tree Status**")
    tree_status = st.radio(
        "Tree Status",
        options=["Healthy ✅", "Needs Attention ⚠️", "Dead ❌"],
        index=0,
        label_visibility="collapsed",
    )

    st.divider()

    water_given = st.selectbox(
        "💧 Water Given Today",
        options=[
            "Normal watering",
            "Double watering (dry soil)",
            "No water today",
            "Drip irrigation only",
            "Other — see notes below",
        ],
    )
    water_notes = st.text_input(
        "Water Notes (optional)",
        placeholder="e.g., Soil was very dry",
    )

    st.divider()

    chemical_details = st.text_input(
        "🧪 Chemical / Fertilizer Applied",
        placeholder="e.g., Urea 50g, Neem oil spray",
    )

    st.divider()

    st.markdown("**📷 Photo of the Tree**")
    photo_method = st.radio(
        "Photo method",
        options=["📸 Take a photo now", "🖼️ Upload from gallery"],
        horizontal=True,
        label_visibility="collapsed",
    )

    photo_file = None
    if "Take" in photo_method:
        photo_file = st.camera_input("Point camera at the tree")
    else:
        photo_file = st.file_uploader(
            "Select photo",
            type=["jpg", "jpeg", "png"],
            label_visibility="collapsed",
        )

    st.divider()

    general_notes = st.text_area(
        "📝 Any Other Notes",
        placeholder="e.g., Yellow leaves, insects, broken branch...",
        height=110,
    )

    submitted = st.form_submit_button("✅  Save Tree Update")


# ══════════════════════════════════════════════════════════
# SUBMISSION LOGIC
# ══════════════════════════════════════════════════════════

if submitted:
    with st.spinner("Saving your update, please wait..."):

        # Upload photo to Drive
        photo_url = "No photo"
        if photo_file is not None:
            try:
                filename = f"Tree_{tree_number}_{log_date}.jpg"
                photo_url = upload_photo_to_drive(photo_file.getvalue(), filename)
            except Exception as e:
                photo_url = "Upload failed"
                st.warning(f"⚠️ Photo could not be uploaded: {e}\nThe rest will still be saved.")

        # Build row in the same order as your sheet columns:
        # Tree Number | Date | Status | Water Given | Water Notes | Chemical | Notes | Photo URL
        row = [
            int(tree_number),
            str(log_date),
            tree_status.split(" ")[0],   # strips emoji
            water_given,
            water_notes.strip(),
            chemical_details.strip(),
            general_notes.strip(),
            photo_url,
        ]

        try:
            append_row_to_sheet(row)
            st.success(
                f"✅ **Tree {tree_number} updated successfully!**\n\n"
                f"Date: {log_date}  |  Status: {tree_status.split(' ')[0]}"
            )
            st.balloons()

        except Exception as e:
            st.error(
                f"❌ Could not save to Google Sheet.\n\nError: {e}\n\n"
                "Check your internet connection and try again."
            )


# ══════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════
st.divider()
st.caption("🥭 Mango Farm Tracker · Data saved to Google Sheets · Built for family farm")st.caption("🥭 Mango Farm Tracker · Data saved to Google Sheets · Built for family farm")
