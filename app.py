import streamlit as st

st.set_page_config(
    page_title="PDF Tools",
    page_icon="📄",
    layout="wide"
)

st.title("📄 PDF Split & Merge")
st.markdown("Internal tools for splitting and merging mail merge PDFs.")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### ✂️ Split PDF
    Split a mail-merge PDF into individual named files using an Excel recipient list and page identifiers.
    
    **Go to:** `Pages > Split PDF`
    """)

with col2:
    st.markdown("""
    ### 🔗 Merge PDFs
    Merge PDFs from multiple folders (e.g. letters + plans + notices) matched by filename.
    
    **Go to:** `Pages > Merge PDFs`
    """)

st.divider()
st.caption("Use the sidebar to navigate between tools.")
