import streamlit as st
from pathlib import Path
import importlib.util

# Define available pages
pages = {
    "Amazon Inventory Ledger": "pages/asin_data.py",
    "Another Page": "pages/another_page.py",
    "Another Page 2":"pages/another_page2.py",
}

# Sidebar menu for navigation
st.sidebar.title("Navigation")
selected_page = st.sidebar.radio("Go to", list(pages.keys()))

# Dynamically load the selected page module
def load_page(page_path):
    page_spec = importlib.util.spec_from_file_location("module.name", page_path)
    page_module = importlib.util.module_from_spec(page_spec)
    page_spec.loader.exec_module(page_module)
    return page_module

# Load and run the selected page
page_module = load_page(pages[selected_page])
if hasattr(page_module, "run"):
    page_module.run()
else:
    st.error("The selected page does not have a 'run' function.")