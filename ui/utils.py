"""UI utility functions for the dashboard."""

import streamlit as st
from datetime import datetime


def display_refresh_button():
    """
    Display a consistent refresh button with last updated timestamp across all pages.
    Returns True if refresh was clicked, False otherwise.
    """
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.caption(f"Last Updated: {st.session_state.last_updated_time}")
    
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.session_state.last_updated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.rerun()
            return True
    
    return False
