import streamlit as st
from PIL import Image
import pytesseract

st.set_page_config(
    page_title="PDF Tools",
    page_icon="📄",
    layout="wide"
)

st.title(" PDF Split & Merge + OCR Tools")
st.markdown("Internal tools for splitting, merging PDFs and extracting text from images.")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### Split PDF
    Split a mail-merge PDF into individual named files using an Excel recipient list and page identifiers.

    **Go to:** `Pages > Split PDF`
    """)

with col2:
    st.markdown("""
    ### Merge PDFs
    Merge PDFs from multiple folders (e.g. letters + plans + notices) matched by filename.

    **Go to:** `Pages > Merge PDFs`
    """)

with col3:
    st.markdown("""
    ### Image to Text (OCR)
    Upload an image and extract text using Tesseract OCR.

    Try it directly below ↓
    """)

st.divider()

# ---------------- OCR SECTION ----------------
st.header(" Quick OCR (Image → Text)")

uploaded_image = st.file_uploader(
    "Upload an image (JPG / PNG)",
    type=["jpg", "jpeg", "png"]
)

if uploaded_image:
    image = Image.open(uploaded_image)

    st.image(image, caption="Uploaded Image", use_container_width=True)

    with st.spinner("Extracting text..."):
        text = pytesseract.image_to_string(image)

    st.success("Done!")

    st.subheader("Extracted Text")
    st.text_area("OCR Output", text, height=250)

st.divider()
st.caption("Use the sidebar to navigate between tools.")
