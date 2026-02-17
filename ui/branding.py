"""UI branding and styling functions for Wolters Kluwer dashboard."""

import streamlit as st
import logging
import base64
import os

logger = logging.getLogger(__name__)


def display_branded_header(page_title=""):
    """Display the branded header with page title and team name."""
    try:
        header_html = f"""
        <style>
        .wk-header {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
            background: linear-gradient(135deg, #3c70a3 0%, #004d99 100%);
            border-bottom: 3px solid #FF6600;
            border-radius: 5px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .wk-page-title {{
            font-size: 28px;
            color: white;
            font-weight: 700;
            margin: 0 0 8px 0;
            letter-spacing: 0.3px;
        }}
        .wk-page-team {{
            font-size: 13px;
            color: #FFB84D;
            font-style: italic;
            margin: 0;
            font-weight: 500;
        }}
        </style>
        
        <div class="wk-header">
            <div class="wk-page-title">{page_title}</div>
            <div class="wk-page-team">InfraOps Engineering Team</div>
        </div>
        """
        
        st.markdown(header_html, unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Error displaying branded header: {str(e)}")
        st.write("📊 Jira Dashboard")


def display_branded_footer():
    """Display the branded footer with team name and copyright information."""
    try:
        footer_css = """
        <style>
        .wk-footer {
            margin-top: 40px;
            padding: 20px;
            background: linear-gradient(135deg, #3c70a3 0%, #004d99 100%);
            border-top: 3px solid #FF6600;
            border-radius: 5px;
            text-align: center;
            box-shadow: 0 -2px 4px rgba(0,0,0,0.1);
        }
        .wk-footer-content {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
        }
        .wk-footer-text {
            color: white;
            font-size: 12px;
            margin: 0;
        }
        .wk-footer-divider {
            color: #FF6600;
            font-size: 12px;
        }
        .wk-footer-team {
            color: #FF6600;
            font-weight: bold;
            font-size: 13px;
        }
        </style>
        
        <div class="wk-footer">
            <div class="wk-footer-content">
                <span class="wk-footer-text">©2026 Wolters Kluwer</span>
                <span class="wk-footer-divider">|</span>
                <span class="wk-footer-team">InfraOps Engineering Team</span>
                <span class="wk-footer-divider">|</span>
                <span class="wk-footer-text">Jira Cloud Dashboard</span>
            </div>
        </div>
        """
        
        st.markdown(footer_css, unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Error displaying branded footer: {str(e)}")


def display_sidebar_branding():
    """Display Wolters Kluwer branding in the sidebar with logo and company name."""
    try:
        # Load logo from assets folder
        logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "wk-logo.png")
        
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as logo_file:
                logo_data = base64.b64encode(logo_file.read()).decode()
            
            sidebar_html = f"""
            <style>
            .wk-sidebar-brand {{
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 10px;
                padding: 20px 15px;
                background: linear-gradient(135deg, #3c70a3 0%, #004d99 100%);
                border-radius: 8px;
                margin-bottom: 20px;
                text-align: center;
                box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            }}
            .wk-sidebar-logo {{
                height: 60px;
                object-fit: contain;
            }}
            .wk-sidebar-company {{
                font-size: 16px;
                font-weight: bold;
                color: white;
                letter-spacing: 0.5px;
                margin: 0;
            }}
            .wk-sidebar-team {{
                font-size: 11px;
                color: #e0e0e0;
                font-style: italic;
                margin: 0;
            }}
            </style>
            
            <div class="wk-sidebar-brand">
                <img src="data:image/png;base64,{logo_data}" alt="Wolters Kluwer" class="wk-sidebar-logo"/>
                <p class="wk-sidebar-company">WOLTERS KLUWER</p>
                <p class="wk-sidebar-team">InfraOps Engineering Team</p>
            </div>
            """
            st.markdown(sidebar_html, unsafe_allow_html=True)
        else:
            # Fallback if logo not found
            st.write("**WOLTERS KLUWER**")
            st.write("InfraOps Engineering Team")
    except Exception as e:
        logger.error(f"Error displaying sidebar branding: {str(e)}")
        st.write("**WOLTERS KLUWER**")
