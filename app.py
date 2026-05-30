"""
Mango Farm Tree Tracker
=======================
A mobile-friendly Streamlit app for logging the health and maintenance
of 200 mango trees. Data saves directly to a Google Sheet.
Photos are uploaded to a Google Drive folder and the link is stored in the sheet.

Author: Built for family farm monitoring
Usage: streamlit run app.py
"""

import io
import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


# ══════════════════════════════════════════════════════════
# PAGE CONFIG  (must be the very first Streamlit call)
# ══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Mango Farm Tracker 🥭",
    page_icon="🥭",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ══════════════════════════════════════════════════════════
# MOBILE-FRIENDLY CUSTOM CSS
# ══════════════════════════════════════════════════════════
st.markdown(
    """
    <style>
        /* ── Global font size boost for mobile ── */
        html, body, [class*="css"] {
            font-size: 17px;
        }

        /* ── Labels: bold & readable ── */
        label, .stRadio > label > div,
        .stSelectbox > label,
        .stTextInput > label,
        .stTextArea > label,
        .stDateInput > label,
        .stFileUploader > label {
            font-size: 1.1rem !important;
            font-weight: 700 !important;
            color: #1b4332 !important;
        }

        /* ── Radio button options ── */
        .stRadio div[role="radiogroup"] label {
            font-size: 1.15rem !important;
            padding: 6px 0;
        }

        /* ── Big green submit button ── */
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
            letter-spacing: 0.5px;
            transition: background-color 0.2s ease;
        }
        div.stButton > button:first-child:hover {
            background-color: #2d6a4f;
            color: #ffffff;
        }

        /* ── Input fields: larger touch targets ── */
        input, textarea, select {
            font-size: 1.05rem !important;
            padding: 10px !important;
        }

        /* ── Section divider ── */
        hr { border-color: #b7e4c7; margin: 1.2rem 0; }

        /* ── Success box ── */
        .element-container .stAlert {
            font-size: 1.1rem !important;
        }

        /* ── Page header ── */
        h1 { color: #1b4332 !important; text-align: center; }
        h3 { color: #2d6a4f !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════

# Name of the worksheet tab inside your Google Sheet.
# Change this if your tab is named something else.
WORKSHEET_NAME = "TreeLog"

# Column names — these must match the headers in your Google Sheet exactly.
COLUMNS = [
    "Tree Number",
    "Date",
    "Status",
    "Water Given",
    "Water Notes",
    "Chemical / Fertilizer",
    "General Notes",
    "Photo URL",
]


# ══════════════════════════════════════════════════════════
# GOOGLE DRIVE HELPER
# ══════════════════════════════════════════════════════════

def upload_photo_to_drive(photo_bytes: bytes, filename: str) -> str:
    """
    Uploads a photo to the Google Drive folder specified in secrets.toml.
    Uses the same service account credentials as the Sheets connection.

    Args:
        photo_bytes: Raw bytes of the image file.
        filename:    What to name the file in Drive (e.g. "Tree_42_2025-06-01.jpg").

    Returns:
        A shareable Google Drive URL string, or an error message string.
    """
    # Pull the service account info from Streamlit secrets.
    # The keys in [connections.gsheets] are standard service-account JSON fields.
    sa_info = dict(st.secrets["connections"]["gsheets"])

    credentials = service_account.Credentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/drive"],
    )

    drive = build("drive", "v3", credentials=credentials)

    # The Drive folder ID is stored separately in secrets.toml
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

    uploaded_file = (
        drive.files()
        .create(body=file_metadata, media_body=media, fields="id")
        .execute()
    )
    file_id = uploaded_file.get("id")

    # Grant public view access so anyone with the link can see the photo
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
# GOOGLE SHEETS CONNECTION
# ══════════════════════════════════════════════════════════

# st.connection reads credentials from .streamlit/secrets.toml automatically.
conn = st.connection("gsheets", type=GSheetsConnection)


# ══════════════════════════════════════════════════════════
# DATA ENTRY FORM
# ══════════════════════════════════════════════════════════

with st.form("tree_log_form", clear_on_submit=True):

    # ── 1. Tree Number ────────────────────────────────────
    tree_number = st.selectbox(
        "🌳 Tree Number",
        options=list(range(1, 201)),
        index=0,
        help="Select the number painted on the tree trunk.",
    )

    # ── 2. Date ───────────────────────────────────────────
    log_date = st.date_input(
        "📅 Date of Update",
        value=date.today(),
    )

    st.divider()

    # ── 3. Tree Status ────────────────────────────────────
    st.markdown("**🩺 Tree Status**")
    tree_status = st.radio(
        "Tree Status",  # actual label (hidden by markdown above)
        options=["Healthy ✅", "Needs Attention ⚠️", "Dead ❌"],
        index=0,
        label_visibility="collapsed",
    )

    st.divider()

    # ── 4. Water Details ──────────────────────────────────
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
        placeholder="e.g., Soil was very dry near the roots",
    )

    st.divider()

    # ── 5. Chemical / Fertilizer ──────────────────────────
    chemical_details = st.text_input(
        "🧪 Chemical / Fertilizer Applied",
        placeholder="e.g., Urea 50g, Neem oil spray, DAP 100g",
    )

    st.divider()

    # ── 6. Photo ──────────────────────────────────────────
    st.markdown("**📷 Photo of the Tree**")
    photo_method = st.radio(
        "Photo method",
        options=["📸 Take a photo now (camera)", "🖼️ Upload from gallery"],
        horizontal=True,
        label_visibility="collapsed",
    )

    photo_file = None
    if "camera" in photo_method:
        photo_file = st.camera_input(
            "Point camera at the tree and tap the button"
        )
    else:
        photo_file = st.file_uploader(
            "Select a photo from your phone",
            type=["jpg", "jpeg", "png"],
            label_visibility="collapsed",
        )

    st.divider()

    # ── 7. General Notes ──────────────────────────────────
    general_notes = st.text_area(
        "📝 Any Other Notes",
        placeholder="e.g., Leaves turning yellow, saw insects, branch broken...",
        height=110,
    )

    # ── 8. Submit Button ──────────────────────────────────
    submitted = st.form_submit_button("✅  Save Tree Update")


# ══════════════════════════════════════════════════════════
# FORM SUBMISSION LOGIC
# ══════════════════════════════════════════════════════════

if submitted:
    with st.spinner("Saving your update, please wait..."):

        # Step A: Upload photo to Google Drive (if one was provided)
        photo_url = "No photo"
        if photo_file is not None:
            try:
                filename = f"Tree_{tree_number}_{log_date}.jpg"
                photo_url = upload_photo_to_drive(photo_file.getvalue(), filename)
            except Exception as e:
                photo_url = "Upload failed"
                st.warning(
                    f"⚠️ Photo could not be uploaded: {e}\n\n"
                    "The rest of the update will still be saved."
                )

        # Step B: Build a one-row DataFrame for the new entry
        new_row = pd.DataFrame(
            [
                {
                    "Tree Number": int(tree_number),
                    "Date": str(log_date),
                    # Strip the emoji from status before saving
                    "Status": tree_status.split(" ")[0],
                    "Water Given": water_given,
                    "Water Notes": water_notes.strip(),
                    "Chemical / Fertilizer": chemical_details.strip(),
                    "General Notes": general_notes.strip(),
                    "Photo URL": photo_url,
                }
            ]
        )

        # Step C: Read current sheet data, append new row, write back
        try:
            existing_data = conn.read(
                worksheet=WORKSHEET_NAME,
                usecols=list(range(len(COLUMNS))),
                ttl=1,  # 1-second cache so we always get the latest rows
            )
            # Remove any completely empty rows that Sheets sometimes adds
            existing_data = existing_data.dropna(how="all")

            updated_data = pd.concat(
                [existing_data, new_row], ignore_index=True
            )

            conn.update(worksheet=WORKSHEET_NAME, data=updated_data)

            # ── Success feedback ──────────────────────────
            st.success(
                f"✅ **Tree {tree_number} updated successfully!**\n\n"
                f"Date: {log_date} | Status: {tree_status.split(' ')[0]}"
            )
            st.balloons()

        except Exception as e:
            st.error(
                f"❌ Could not save to Google Sheet.\n\n"
                f"Error: {e}\n\n"
                "Please check your internet connection and try again."
            )


# ══════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════
st.divider()
st.caption("🥭 Mango Farm Tracker · Data saved to Google Sheets · Built for family farm")
