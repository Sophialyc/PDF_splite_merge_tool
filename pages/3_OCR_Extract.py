import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageEnhance
import io
import os

st.set_page_config(page_title="OCR Extract", page_icon="🔍", layout="wide")

st.title(" OCR Text Extractor")
st.markdown("Convert scanned PDFs or images into searchable text.")

with st.expander("⚙️ Settings", expanded=False):
    dpi = st.slider("Render DPI (higher = better quality, slower)", 150, 600, 300, step=50)

st.divider()

uploaded_file = st.file_uploader(
    "Upload a scanned PDF or image",
    type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp"],
    help="Supports PDFs (single or multi-page) and common image formats.",
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def preprocess_image(image_bytes: bytes) -> bytes:
    image = Image.open(io.BytesIO(image_bytes)).convert("L")
    image = ImageEnhance.Contrast(image).enhance(2.0)
    image = image.point(lambda x: 0 if x < 180 else 255, "1")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def ocr_page_bytes(image_bytes: bytes) -> str:
    processed = preprocess_image(image_bytes)
    image = Image.open(io.BytesIO(processed))
    return pytesseract.image_to_string(image, lang="eng").strip()


def has_meaningful_text(text: str, min_words: int = 5, min_chars: int = 20) -> bool:
    if not text:
        return False
    return len(text.split()) >= min_words or len(text) >= min_chars


def render_pdf_page_as_image(file_bytes: bytes, page_index: int, dpi: int = 150) -> bytes:
    """Render a single PDF page to a PNG image for display."""
    pdf = fitz.open(stream=file_bytes, filetype="pdf")
    page = pdf[page_index]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    pdf.close()
    return pix.tobytes("png")


def extract_from_pdf(file_bytes: bytes, dpi: int, progress_bar, status_text):
    pdf = fitz.open(stream=file_bytes, filetype="pdf")
    total = len(pdf)
    page_texts = []
    for i in range(total):
        status_text.text(f"Processing page {i + 1} of {total}…")
        progress_bar.progress((i + 1) / total)
        page = pdf[i]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        try:
            text = ocr_page_bytes(img_bytes)
        except Exception as e:
            text = ""
            st.warning(f"Page {i + 1}: OCR failed — {e}")
        page_texts.append(
            text if has_meaningful_text(text)
            else "[No text detected — may contain maps/images/stamps]"
        )
    pdf.close()

    sep = "=" * 70
    lines = [f"{sep}\nPage {i + 1}:\n{sep}\n{t}\n" for i, t in enumerate(page_texts)]
    return "\n".join(lines), page_texts, total


def extract_from_image(file_bytes: bytes, progress_bar, status_text):
    status_text.text("Running OCR on image…")
    progress_bar.progress(0.5)
    try:
        text = ocr_page_bytes(file_bytes)
    except Exception as e:
        st.error(f"OCR failed: {e}")
        return "", [], 1
    progress_bar.progress(1.0)
    result = text if has_meaningful_text(text) else "[No text detected]"
    return result, [result], 1


# ── Run OCR ───────────────────────────────────────────────────────────────────

if uploaded_file:
    file_bytes = uploaded_file.read()
    filename_stem = os.path.splitext(uploaded_file.name)[0]
    is_pdf = uploaded_file.name.lower().endswith(".pdf")

    st.info(f"📄 **{uploaded_file.name}** — {len(file_bytes) / 1024:.1f} KB uploaded")

    if st.button("▶ Run OCR", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        try:
            if is_pdf:
                full_text, page_texts, total_pages = extract_from_pdf(file_bytes, dpi, progress_bar, status_text)
            else:
                full_text, page_texts, total_pages = extract_from_image(file_bytes, progress_bar, status_text)

            progress_bar.progress(1.0)
            status_text.text("✅ Done!")

            st.session_state["ocr_full_text"] = full_text
            st.session_state["ocr_page_texts"] = page_texts
            st.session_state["ocr_file_bytes"] = file_bytes
            st.session_state["ocr_filename_stem"] = filename_stem
            st.session_state["ocr_is_pdf"] = is_pdf
            st.session_state["ocr_total_pages"] = total_pages
            st.session_state["ocr_current_page"] = 1

        except Exception as e:
            st.error(f"Something went wrong: {e}")

# ── Split view ────────────────────────────────────────────────────────────────

if st.session_state.get("ocr_full_text"):
    full_text    = st.session_state["ocr_full_text"]
    page_texts   = st.session_state["ocr_page_texts"]
    file_bytes   = st.session_state["ocr_file_bytes"]
    filename_stem = st.session_state["ocr_filename_stem"]
    is_pdf       = st.session_state["ocr_is_pdf"]
    total_pages  = st.session_state["ocr_total_pages"]

    st.success(f"Extracted {len(full_text.split())} words across {total_pages} page(s).")
    st.download_button(
        label="⬇️ Download extracted text (.txt)",
        data=full_text.encode("utf-8"),
        file_name=f"{filename_stem}_OCR.txt",
        mime="text/plain",
    )

    st.divider()

    # Page selector (above the split so it controls both sides)
    if total_pages > 1:
        current_page = st.number_input(
            f"Page (1 – {total_pages})",
            min_value=1,
            max_value=total_pages,
            value=st.session_state.get("ocr_current_page", 1),
            step=1,
            key="ocr_current_page",
        )
    else:
        current_page = 1

    left_col, right_col = st.columns(2, gap="medium")

    with left_col:
        st.markdown(f"**📄 Document — page {current_page} of {total_pages}**")
        if is_pdf:
            img_bytes = render_pdf_page_as_image(file_bytes, current_page - 1, dpi=150)
            st.image(img_bytes, use_container_width=True)
        else:
            st.image(file_bytes, use_container_width=True)

    with right_col:
        st.markdown(f"**📝 Extracted text — page {current_page}**")
        st.text_area(
            "extracted",
            value=page_texts[current_page - 1],
            height=700,
            label_visibility="collapsed",
        )
