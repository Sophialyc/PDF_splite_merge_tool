import streamlit as st
import pandas as pd
import re
import os
import zipfile
import io
from pypdf import PdfReader, PdfWriter

st.set_page_config(page_title="Split PDF", page_icon="✂️", layout="wide")
st.title("Split PDF")
st.markdown("Split a mail-merge PDF into individually named files using an Excel recipient list.")

# ── Inputs ────────────────────────────────────────────────────────────────────
st.subheader("1. Upload files")
col1, col2 = st.columns(2)

with col1:
    pdf_file = st.file_uploader("Mail-merge PDF", type=["pdf"])

with col2:
    excel_file = st.file_uploader("Excel recipient list", type=["xlsx", "xls"])
    if excel_file:
        try:
            df_preview = pd.read_excel(excel_file)
            excel_file.seek(0)
            cols = df_preview.columns.tolist()
            name_col = st.selectbox(
                "Column containing recipient names",
                options=cols,
                index=0,
                help="This column's values will become the output filenames."
            )
        except Exception as e:
            st.error(f"Could not read Excel file: {e}")
            name_col = None
    else:
        name_col = None

st.subheader("2. Split markers")
st.markdown("These text strings tell the tool where each new record starts and ends.")

col3, col4 = st.columns(2)
with col3:
    identifier = st.text_input(
        "Start-of-record identifier",
        value="IMPORTANT: THIS COMMUNICATION AFFECTS YOUR PROPERTY",
        help="Exact text that appears at the top of every new recipient's document."
    )
with col4:
    end_marker = st.text_input(
        "End-of-record marker",
        value="Dated : 21 May 2026",
        help="Exact text that appears on the last line of every recipient's document. Leave blank to split only on the start identifier."
    )

st.subheader("3. Split mode")
split_mode = st.radio(
    "How should the PDF be split?",
    options=["By text identifiers (recommended)", "Every N pages"],
    horizontal=True
)

pages_per_record = None
if split_mode == "Every N pages":
    pages_per_record = st.number_input("Pages per record", min_value=1, value=2, step=1)

# ── Run ───────────────────────────────────────────────────────────────────────
st.divider()
run = st.button("▶ Run Split", type="primary", disabled=not (pdf_file and excel_file))

if run:
    if not pdf_file or not excel_file:
        st.error("Please upload both the PDF and the Excel file.")
        st.stop()

    if split_mode == "By text identifiers (recommended)" and not identifier.strip():
        st.error("Please enter a start-of-record identifier.")
        st.stop()

    progress = st.progress(0, text="Reading files…")
    log_lines = []

    # Read names
    df = pd.read_excel(excel_file)
    name_list = df[name_col].astype(str).tolist()
    progress.progress(5, text=f"Loaded {len(name_list)} names from Excel.")

    # Read PDF
    try:
        pdf = PdfReader(pdf_file)
    except Exception as e:
        st.error(f"Could not read PDF: {e}")
        st.stop()

    total_pages = len(pdf.pages)
    progress.progress(10, text=f"PDF loaded — {total_pages} pages.")

    # ── Build splits ──────────────────────────────────────────────────────────
    splits = []  # list of lists of page indices

    if split_mode == "Every N pages":
        for start in range(0, total_pages, pages_per_record):
            splits.append(list(range(start, min(start + pages_per_record, total_pages))))

    else:  # Text identifiers
        record_pages = []
        in_record = False

        for i, page in enumerate(pdf.pages):
            pct = 10 + int((i / total_pages) * 50)
            if i % 50 == 0:
                progress.progress(pct, text=f"Scanning page {i+1} of {total_pages}…")

            text = page.extract_text() or ""
            lines = [l.strip() for l in text.splitlines() if l.strip()]

            if identifier.strip() in text:
                if record_pages:
                    splits.append(record_pages)
                    record_pages = []
                in_record = True

            if in_record:
                record_pages.append(i)
                if end_marker.strip() and lines and lines[-1] == end_marker.strip():
                    splits.append(record_pages)
                    record_pages = []
                    in_record = False

        if record_pages:
            splits.append(record_pages)

    progress.progress(60, text=f"Found {len(splits)} records. Building output files…")

    if len(splits) == 0:
        st.error("No records found. Check that your identifier text matches the PDF exactly (case-sensitive).")
        st.stop()

    if len(splits) != len(name_list):
        st.warning(
            f"⚠️ Mismatch: found **{len(splits)} records** in PDF but **{len(name_list)} names** in Excel. "
            "Extra records will be named `record_N`. Check the identifiers or the Excel list."
        )

    # ── Write to in-memory ZIP ────────────────────────────────────────────────
    zip_buffer = io.BytesIO()
    name_counts = {}

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, pages in enumerate(splits):
            pct = 60 + int((idx / len(splits)) * 35)
            if idx % 20 == 0:
                progress.progress(pct, text=f"Writing file {idx+1} of {len(splits)}…")

            writer = PdfWriter()
            for page_num in pages:
                writer.add_page(pdf.pages[page_num])

            base_name = name_list[idx] if idx < len(name_list) else f"record_{idx+1}"
            safe_name = re.sub(r'[\\/*?:"<>|]', "", str(base_name)).strip()

            count = name_counts.get(safe_name, 0)
            name_counts[safe_name] = count + 1
            file_name = f"{safe_name} ({count+1}).pdf" if count > 0 else f"{safe_name}.pdf"

            pdf_bytes = io.BytesIO()
            writer.write(pdf_bytes)
            zf.writestr(file_name, pdf_bytes.getvalue())
            log_lines.append(file_name)

        # Write log inside ZIP
        zf.writestr("split_log.txt", "\n".join(log_lines))

    zip_buffer.seek(0)
    progress.progress(100, text="Done!")

    st.success(f"✅ Split complete — **{len(splits)} files** created.")

    # ── Summary table ─────────────────────────────────────────────────────────
    with st.expander("View file list", expanded=False):
        st.dataframe(
            pd.DataFrame({"Filename": log_lines, "Pages": [len(p) for p in splits]}),
            use_container_width=True,
            hide_index=True
        )

    st.download_button(
        label="⬇️ Download all split PDFs (ZIP)",
        data=zip_buffer,
        file_name="split_pdfs.zip",
        mime="application/zip"
    )
