"""Login page with OAuth 2.0 "Login with Jira" button."""

import streamlit as st
from ui.branding import display_branded_header
from auth import get_authorization_url, JiraOAuthError


def render_login_page(oauth_config: dict, jira_config: dict):
    """
    Render the OAuth login page with "Login with Jira" button.
    
    Args:
        oauth_config: OAuth configuration from config.yaml
        jira_config: Jira configuration from config.yaml
    """
    # Display branded header
    display_branded_header("Login")
    
    # Create centered container for login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        
        st.markdown("""
        <div style="text-align: center; padding: 40px 0;">
            <h2 style="margin-bottom: 10px;">Welcome to Jira Dashboard</h2>
            <p style="color: #666; margin-bottom: 40px;">
                Secure access via Atlassian login
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Generate authorization URL
        try:
            auth_url = get_authorization_url(oauth_config)
            
            # Display login button as a link
            st.markdown(f"""
            <div style="text-align: center; margin: 20px 0;">
                <a href="{auth_url}" style="
                    display: inline-block;
                    padding: 12px 32px;
                    background-color: #0052CC;
                    color: white;
                    text-decoration: none;
                    border-radius: 3px;
                    font-weight: 600;
                    font-size: 16px;
                ">🔐 Login with Jira</a>
            </div>
            """, unsafe_allow_html=True)
            
        except JiraOAuthError as e:
            st.error(f"❌ Login Error: {str(e)}")
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
        
        st.markdown("---")
        
        st.markdown("""
        <div style="text-align: center; padding: 20px 0; color: #999; font-size: 12px;">
            <p>
                You will be redirected to Atlassian's secure login page.<br>
                Your credentials are managed by Atlassian.
            </p>
        </div>
        """, unsafe_allow_html=True)
