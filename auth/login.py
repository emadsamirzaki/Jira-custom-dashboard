"""Login page with OAuth 2.0 "Login with Jira" and "Login with Microsoft" buttons."""

import streamlit as st
from ui.branding import display_branded_header
from auth import get_authorization_url, JiraOAuthError
from auth.microsoft_oauth import get_microsoft_authorization_url, MicrosoftOAuthError
from auth.oauth import create_state_with_provider


def render_login_page(oauth_config: dict, jira_config: dict, microsoft_config: dict = None):
    """
    Render the OAuth login page with login buttons.
    
    Args:
        oauth_config: OAuth configuration from config.yaml (may contain jira and microsoft nested configs)
        jira_config: Jira configuration from config.yaml
        microsoft_config: Microsoft OAuth configuration from config.yaml (optional)
    """
    # Extract nested Jira OAuth config if available, otherwise use oauth_config directly for backward compatibility
    jira_oauth_config = oauth_config.get('jira', oauth_config) if 'jira' in oauth_config else oauth_config
    jira_oauth_enabled = jira_oauth_config.get('enabled', True) if 'jira' in oauth_config else True
    microsoft_oauth_enabled = microsoft_config and microsoft_config.get('enabled', False)
    
    # If neither is enabled, show an error
    if not jira_oauth_enabled and not microsoft_oauth_enabled:
        st.error("❌ No login methods are enabled. Please contact your administrator.")
        st.stop()
    # Enhanced login page styling
    st.markdown("""
        <style>
        [data-testid="stSidebar"] {
            display: none !important;
        }
        
        .login-container {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .login-card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
            padding: 50px 40px;
            max-width: 500px;
            text-align: center;
        }
        
        .login-title {
            font-size: 32px;
            font-weight: 700;
            color: #1a1a1a;
            margin-bottom: 8px;
        }
        
        .login-subtitle {
            font-size: 16px;
            color: #666;
            margin-bottom: 40px;
            line-height: 1.5;
        }
        
        .login-section {
            margin: 30px 0;
        }
        
        .login-section-title {
            font-size: 13px;
            font-weight: 600;
            color: #999;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 20px;
        }
        
        .login-buttons {
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
        }
        
        .login-button {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 16px 28px;
            background-color: #f5f5f5;
            color: #333;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            font-size: 15px;
            border: 2px solid transparent;
            transition: all 0.3s ease;
            margin: 8px;
            min-width: 180px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        
        .login-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
        }
        
        .jira-button {
            background: linear-gradient(135deg, #0052CC 0%, #0047A3 100%);
            color: white;
            border-color: #0052CC;
        }
        
        .jira-button:hover {
            background: linear-gradient(135deg, #0047A3 0%, #003D8B 100%);
            border-color: #003D8B;
        }
        
        .microsoft-button {
            background: linear-gradient(135deg, #00A4EF 0%, #0078D4 100%);
            color: white;
            border-color: #00A4EF;
        }
        
        .microsoft-button:hover {
            background: linear-gradient(135deg, #0078D4 0%, #005FA3 100%);
            border-color: #0078D4;
        }
        
        .login-divider {
            margin: 30px 0;
            border: none;
            border-top: 2px solid #eee;
        }
        
        .login-footer {
            font-size: 12px;
            color: #999;
            line-height: 1.6;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }
        
        .button-label {
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 15px;
            color: #333;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Display branded header
    display_branded_header("Login")
    
    # Create centered container for login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Main title and subtitle
        st.markdown("""
        <div style="text-align: center; margin-bottom: 40px;">
            <h1 style="font-size: 36px; font-weight: 700; color: #1a1a1a; margin: 0 0 12px 0;">
                Welcome Back 👋
            </h1>
            <p style="font-size: 16px; color: #666; margin: 0; line-height: 1.6;">
                Sign in to access your Jira Dashboard with your preferred account
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Create two columns for buttons side by side if both are enabled, otherwise show available ones
        if jira_oauth_enabled and microsoft_oauth_enabled:
            st.markdown("""
            <div style="text-align: center; margin: 40px 0;">
                <p style="font-size: 13px; font-weight: 600; color: #999; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 25px;">
                    Choose your login method
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            button_col1, spacer, button_col2 = st.columns([1, 0.2, 1])
            
            # Jira OAuth button
            with button_col1:
                try:
                    state = create_state_with_provider('jira')
                    auth_url = get_authorization_url(jira_oauth_config, state)
                    
                    st.markdown("""
                    <div style="text-align: center;">
                        <p style="font-size: 12px; font-weight: 600; color: #666; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px;">
                            Jira Account
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div style="text-align: center;">
                        <a href="{auth_url}" style="
                            display: inline-block;
                            padding: 14px 32px;
                            background: linear-gradient(135deg, #0052CC 0%, #0047A3 100%);
                            color: white;
                            text-decoration: none;
                            border-radius: 8px;
                            font-weight: 600;
                            font-size: 15px;
                            border: 2px solid transparent;
                            transition: all 0.3s ease;
                            box-shadow: 0 2px 8px rgba(0, 82, 204, 0.3);
                            cursor: pointer;
                        ">
                            🔐 Sign in with Jira
                        </a>
                    </div>
                    """, unsafe_allow_html=True)
                    
                except JiraOAuthError as e:
                    st.error(f"❌ Jira Login Error: {str(e)}")
                except Exception as e:
                    st.error(f"❌ Jira Error: {str(e)}")
            
            # Microsoft OAuth button
            with button_col2:
                try:
                    state = create_state_with_provider('microsoft')
                    microsoft_auth_url = get_microsoft_authorization_url(microsoft_config, state)
                    
                    st.markdown("""
                    <div style="text-align: center;">
                        <p style="font-size: 12px; font-weight: 600; color: #666; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px;">
                            Microsoft Account
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div style="text-align: center;">
                        <a href="{microsoft_auth_url}" style="
                            display: inline-block;
                            padding: 14px 32px;
                            background: linear-gradient(135deg, #00A4EF 0%, #0078D4 100%);
                            color: white;
                            text-decoration: none;
                            border-radius: 8px;
                            font-weight: 600;
                            font-size: 15px;
                            border: 2px solid transparent;
                            transition: all 0.3s ease;
                            box-shadow: 0 2px 8px rgba(0, 164, 239, 0.3);
                            cursor: pointer;
                        ">
                            🔑 Sign in with Microsoft
                        </a>
                    </div>
                    """, unsafe_allow_html=True)
                    
                except MicrosoftOAuthError as e:
                    st.error(f"❌ Microsoft Login Error: {str(e)}")
                except Exception as e:
                    st.error(f"❌ Microsoft Error: {str(e)}")
        
        elif jira_oauth_enabled:
            # Only Jira button if Microsoft is not enabled
            try:
                state = create_state_with_provider('jira')
                auth_url = get_authorization_url(jira_oauth_config, state)
                
                st.markdown("""
                <div style="text-align: center; margin: 30px 0;">
                </div>
                """, unsafe_allow_html=True)
                
                # Display login button as a link
                st.markdown(f"""
                <div style="text-align: center;">
                    <a href="{auth_url}" style="
                        display: inline-block;
                        padding: 16px 48px;
                        background: linear-gradient(135deg, #0052CC 0%, #0047A3 100%);
                        color: white;
                        text-decoration: none;
                        border-radius: 8px;
                        font-weight: 600;
                        font-size: 16px;
                        border: 2px solid transparent;
                        transition: all 0.3s ease;
                        box-shadow: 0 4px 16px rgba(0, 82, 204, 0.3);
                        cursor: pointer;
                    ">
                        🔐 Sign in with Jira Account
                    </a>
                </div>
                """, unsafe_allow_html=True)
                
            except JiraOAuthError as e:
                st.error(f"❌ Login Error: {str(e)}")
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")
        
        elif microsoft_oauth_enabled:
            # Only Microsoft button if Jira is not enabled
            try:
                state = create_state_with_provider('microsoft')
                microsoft_auth_url = get_microsoft_authorization_url(microsoft_config, state)
                
                st.markdown("""
                <div style="text-align: center; margin: 30px 0;">
                </div>
                """, unsafe_allow_html=True)
                
                # Display login button as a link
                st.markdown(f"""
                <div style="text-align: center;">
                    <a href="{microsoft_auth_url}" style="
                        display: inline-block;
                        padding: 16px 48px;
                        background: linear-gradient(135deg, #00A4EF 0%, #0078D4 100%);
                        color: white;
                        text-decoration: none;
                        border-radius: 8px;
                        font-weight: 600;
                        font-size: 16px;
                        border: 2px solid transparent;
                        transition: all 0.3s ease;
                        box-shadow: 0 4px 16px rgba(0, 164, 239, 0.3);
                        cursor: pointer;
                    ">
                        🔑 Sign in with Microsoft Account
                    </a>
                </div>
                """, unsafe_allow_html=True)
                
            except MicrosoftOAuthError as e:
                st.error(f"❌ Microsoft Login Error: {str(e)}")
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")
        
        # Footer information
        if jira_oauth_enabled and microsoft_oauth_enabled:
            footer_html = "🔒 <strong>Secure & Safe</strong><br>Login with either your Jira account or Microsoft account.<br>Your credentials are managed securely by the respective providers."
        elif microsoft_oauth_enabled:
            footer_html = "🔒 <strong>Secure & Safe</strong><br>Sign in with your Microsoft account.<br>Your credentials are managed securely by Microsoft."
        else:  # jira_oauth_enabled
            footer_html = "🔒 <strong>Secure & Safe</strong><br>Sign in with your Jira account.<br>Your credentials are managed securely by Atlassian."
        
        st.markdown(f"""
        <div style="margin-top: 50px; padding-top: 30px; border-top: 1px solid #eee; text-align: center;">
            <p style="font-size: 12px; color: #999; line-height: 1.6; margin: 0;">
                {footer_html}
            </p>
        </div>
        """, unsafe_allow_html=True)
