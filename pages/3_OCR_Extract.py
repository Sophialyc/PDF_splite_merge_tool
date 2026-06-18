import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageEnhance
import io
import os

st.set_page_config(page_title="OCR Extract", page_icon="🔍", layout="wide")

st.title("🔍 OCR Text Extractor")
st.markdown("Convert scanned PDFs or images into searchable text.")

with st.expander("⚙️ Settings", expanded=False):
    dpi = st.slider("Render DPI (higher = better quality, slower)", 150, 600, 300, step=50)

st.divider()

uploaded_file = st.file_uploader(
    "Upload a scanned PDF or image",
    type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp"],
    help="Supports PDFs (single or multi-page) and common image formats.",
)

# ── Core OCR helpers ──────────────────────────────────────────────────────────

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


def extract_from_pdf(file_bytes: bytes, dpi: int, progress_bar, status_text) -> str:
    pdf = fitz.open(stream=file_bytes, filetype="pdf")
    total = len(pdf)
    lines = []
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
        sep = "=" * 70
        if has_meaningful_text(text):
            lines.append(f"{sep}\nPage {i + 1}:\n{sep}\n{text}\n")
        else:
            lines.append(f"Page {i + 1}: [No text detected — may contain maps/images/stamps]\n")
    pdf.close()
    return "\n".join(lines)


def extract_from_image(file_bytes: bytes, progress_bar, status_text) -> str:
    status_text.text("Running OCR on image…")
    progress_bar.progress(0.5)
    try:
        text = ocr_page_bytes(file_bytes)
    except Exception as e:
        st.error(f"OCR failed: {e}")
        return ""
    progress_bar.progress(1.0)
    return text if has_meaningful_text(text) else "[No text detected]"


# ── Run extraction ────────────────────────────────────────────────────────────

if uploaded_file:
    file_bytes = uploaded_file.read()
    filename_stem = os.path.splitext(uploaded_file.name)[0]
    is_pdf = uploaded_file.name.lower().endswith(".pdf")

    st.info(f"📄 **{uploaded_file.name}** — {len(file_bytes) / 1024:.1f} KB uploaded")

    if st.button("▶ Run OCR", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        with st.spinner("Extracting text…"):
            try:
                if is_pdf:
                    extracted = extract_from_pdf(file_bytes, dpi, progress_bar, status_text)
                else:
                    extracted = extract_from_image(file_bytes, progress_bar, status_text)

                progress_bar.progress(1.0)
                status_text.text("✅ Done!")

                st.success(f"Extracted {len(extracted.split())} words.")

                with st.expander("📋 Preview extracted text", expanded=True):
                    st.text_area("Output", extracted, height=400, label_visibility="collapsed")

                st.download_button(
                    label="⬇️ Download as .txt",
                    data=extracted.encode("utf-8"),
                    file_name=f"{filename_stem}_OCR.txt",
                    mime="text/plain",
                )

            except Exception as e:
                st.error(f"Something went wrong: {e}")
