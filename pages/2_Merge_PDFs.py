import streamlit as st
import io
import zipfile
from pypdf import PdfWriter, PdfReader

st.set_page_config(page_title="Merge PDFs", page_icon="🔗", layout="wide")
st.title("Merge PDFs")
st.markdown(
    "Upload PDFs from multiple groups (e.g. Letters, Plans, Notices). "
    "Files with the **same name** across groups will be merged together in the order the groups are listed."
)

# ── Group management ──────────────────────────────────────────────────────────
st.subheader("1. Define groups")

if "groups" not in st.session_state:
    st.session_state.groups = [
        {"label": "Letters", "files": []},
        {"label": "Plans", "files": []},
    ]

def add_group():
    st.session_state.groups.append({"label": f"Group {len(st.session_state.groups)+1}", "files": []})

def remove_group(idx):
    st.session_state.groups.pop(idx)

# Render each group
for i, group in enumerate(st.session_state.groups):
    with st.container(border=True):
        col_label, col_remove = st.columns([5, 1])
        with col_label:
            st.session_state.groups[i]["label"] = st.text_input(
                f"Group {i+1} name",
                value=group["label"],
                key=f"label_{i}",
                label_visibility="collapsed",
                placeholder=f"Group {i+1} name (e.g. Letters)"
            )
        with col_remove:
            if len(st.session_state.groups) > 2:
                st.button("✕", key=f"remove_{i}", on_click=remove_group, args=(i,), help="Remove this group")

        uploaded = st.file_uploader(
            f"Upload PDFs for **{st.session_state.groups[i]['label']}**",
            type=["pdf"],
            accept_multiple_files=True,
            key=f"upload_{i}",
            label_visibility="collapsed"
        )
        if uploaded:
            st.session_state.groups[i]["files"] = uploaded
            st.caption(f"{len(uploaded)} file(s) uploaded")

st.button("➕ Add another group", on_click=add_group)

# ── Merge order preview ───────────────────────────────────────────────────────
st.subheader("2. Merge order")
st.markdown(
    "Within each merged output file, pages will be assembled in this group order:"
)
order_labels = [g["label"] for g in st.session_state.groups if g["label"].strip()]
st.markdown("  →  ".join([f"**{l}**" for l in order_labels]))

# ── Run ───────────────────────────────────────────────────────────────────────
st.divider()

# Validate: at least one group has files
groups_with_files = [g for g in st.session_state.groups if g.get("files")]
can_run = len(groups_with_files) >= 1

run = st.button("▶ Run Merge", type="primary", disabled=not can_run)

if run:
    progress = st.progress(0, text="Indexing files…")

    # Build index: {stem: {group_label: file_bytes}}
    file_index = {}  # stem -> list of (group_order, label, file_bytes)

    for g_idx, group in enumerate(st.session_state.groups):
        label = group["label"] or f"Group {g_idx+1}"
        for f in group.get("files", []):
            stem = f.name.rsplit(".", 1)[0]
            if stem not in file_index:
                file_index[stem] = []
            file_index[stem].append((g_idx, label, f.read()))

    # Sort each stem's entries by group order
    for stem in file_index:
        file_index[stem].sort(key=lambda x: x[0])

    total = len(file_index)
    if total == 0:
        st.error("No files found. Please upload PDFs in at least one group.")
        st.stop()

    progress.progress(10, text=f"Found {total} unique filenames to merge.")

    # ── Build ZIP ─────────────────────────────────────────────────────────────
    zip_buffer = io.BytesIO()
    log_lines = []
    warnings = []

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, (stem, entries) in enumerate(sorted(file_index.items())):
            pct = 10 + int((idx / total) * 85)
            if idx % 20 == 0:
                progress.progress(pct, text=f"Merging {idx+1} of {total}: {stem}…")

            # Note if file only appears in some groups
            present_labels = [e[1] for e in entries]
            all_labels = [g["label"] or f"Group {i+1}" for i, g in enumerate(st.session_state.groups) if g.get("files")]
            missing = [l for l in all_labels if l not in present_labels]
            if missing:
                warnings.append(f"**{stem}** — missing from: {', '.join(missing)}")

            try:
                writer = PdfWriter()
                for _, label, pdf_bytes in entries:
                    reader = PdfReader(io.BytesIO(pdf_bytes))
                    for page in reader.pages:
                        writer.add_page(page)

                out_bytes = io.BytesIO()
                writer.write(out_bytes)
                zf.writestr(f"{stem}.pdf", out_bytes.getvalue())
                log_lines.append(f"{stem}.pdf  ({len(entries)} group(s): {', '.join(present_labels)})")

            except Exception as e:
                warnings.append(f"**{stem}** — error merging: {e}")

        # Log file
        zf.writestr("merge_log.txt", "\n".join(log_lines))

    zip_buffer.seek(0)
    progress.progress(100, text="Done!")

    st.success(f"✅ Merge complete — **{len(log_lines)} files** created.")

    if warnings:
        with st.expander(f"⚠️ {len(warnings)} warning(s) — files missing from some groups", expanded=True):
            for w in warnings:
                st.markdown(f"- {w}")

    with st.expander("View merge log", expanded=False):
        for line in log_lines:
            st.text(line)

    st.download_button(
        label="⬇️ Download all merged PDFs (ZIP)",
        data=zip_buffer,
        file_name="merged_pdfs.zip",
        mime="application/zip"
    )
