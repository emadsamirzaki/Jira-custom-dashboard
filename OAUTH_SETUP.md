# OAuth 2.0 Setup Guide

This document explains how to set up and enable OAuth 2.0 authentication for the Jira Dashboard.

## Overview

The dashboard now supports OAuth 2.0 authentication via Atlassian's identity provider. Users can log in using their Atlassian account credentials instead of API tokens.

### Features
- ✅ Secure "Login with Jira" button on login page
- ✅ Automatic redirect to Atlassian login page
- ✅ User credentials managed by Atlassian (not stored locally)
- ✅ Access restricted to wkengineering.atlassian.net users
- ✅ User info and avatar display in sidebar
- ✅ One-click logout functionality
- ✅ Fallback to API token auth if OAuth is disabled

## Setup Steps

### Step 1: Create OAuth App in Atlassian Developer Console

1. Go to: **https://developer.atlassian.com/console/myapps/**
2. Click **Create app**
3. Select **OAuth 2.0** → **Web** app type
4. Fill in app name: `Jira Dashboard`
5. Click **Create**

### Step 2: Configure Callback URLs

In your OAuth app settings:

1. Go to **Authorization** section
2. Add **Callback URLs**:
   - For **local testing**: `http://localhost:8501`
   - For **production**: `https://yourdashboard.company.com` (replace with your actual domain)
3. Click **Save**

### Step 3: Set Scopes

1. Go to **Permissions** section
2. Add required scopes:
   - `read:jira-work` - Read access to Jira issues
   - `read:jira-user` - Read user information
   - `offline_access` - Refresh token support
3. Click **Save**

### Step 4: Get Credentials

1. Go to **Settings** section
2. Copy your:
   - **Client ID**
   - **Client Secret** (keep this secret!)

### Step 5: Configure config.yaml

In your `config.yaml`, add your OAuth credentials:

```yaml
oauth:
  enabled: true  # Enable OAuth authentication
  client_id: "YOUR_CLIENT_ID"  # From Atlassian Developer Console
  client_secret: "YOUR_CLIENT_SECRET"  # From Atlassian Developer Console
  redirect_uri: "http://localhost:8501"  # Match callback URL
  scope: "read:jira-work read:jira-user offline_access"
  auth_url: "https://auth.atlassian.com/authorize"
  token_url: "https://auth.atlassian.com/oauth/token"
  resource_url: "https://api.atlassian.com/me"

jira:
  url: "https://wkengineering.atlassian.net/"
  project_key: "ESP"
  board_id: 81
  allowed_instance: "wkengineering.atlassian.net"  # Restrict access to this instance
```

### Step 6: Restart Application

```bash
# Kill existing Streamlit process
Get-Process python | Where-Object {$_.CommandLine -like "*streamlit*"} | Stop-Process -Force

# Start app
streamlit run app.py
```

## Usage

### For Users

1. **First Visit**: User sees login page with "🔐 Login with Jira" button
2. **Click Button**: Redirected to Atlassian's secure login page
3. **Enter Credentials**: User logs in with their Atlassian account
4. **Authorization**: User grants dashboard access to their account
5. **Dashboard Access**: User is logged in and sees the dashboard
6. **User Info**: User name, email, and avatar appear in sidebar
7. **Logout**: Click "🚪 Logout" in sidebar to log out

### For Administrators

- **Monitor Logins**: Check application logs for authentication events
- **Access Control**: Only users from wkengineering.atlassian.net can access
- **Token Management**: Refresh tokens are handled automatically
- **Error Logs**: Check `LOG_LEVEL` environment variable (set to INFO for more details)

## Technical Details

### OAuth Flow

```
1. User clicks "Login with Jira"
   ↓
2. Redirected to Atlassian auth page
   ↓
3. User logs in with their credentials
   ↓
4. Atlassian redirects back with auth code
   ↓
5. App exchanges auth code for access token
   ↓
6. App retrieves user information
   ↓
7. App validates user's Jira instance
   ↓
8. Auth token stored in st.session_state only (not on disk)
   ↓
9. User sees dashboard
```

### Session Management

- **Access Token**: Stored in `st.session_state.access_token` (session only)
- **Refresh Token**: Stored in `st.session_state.refresh_token` (for future use)
- **User Info**: Stored in `st.session_state.user_info` (name, email, avatar)
- **Authenticated**: Flag in `st.session_state.authenticated`

### Code Files

- **auth/__init__.py** - Module exports
- **auth/oauth.py** - OAuth logic (token exchange, user validation)
- **auth/login.py** - Login page UI
- **app.py** - Main app with OAuth integration

## Troubleshooting

### Issue: "Callback URL mismatch"
**Solution**: Ensure callback URL in Atlassian console matches `redirect_uri` in config.yaml

### Issue: "Invalid client_id/client_secret"
**Solution**: Double-check credentials are copied correctly (no extra spaces)

### Issue: "Access restricted to wkengineering Jira users only"
**Solution**: This is intentional. Ensure you're logging in with a wkengineering.atlassian.net account

### Issue: "Token exchange timeout"
**Solution**: Check internet connection and ensure Atlassian API is accessible

### Issue: User logged in but can't access data
**Solution**: Ensure user has proper permissions in the Jira project (ESP)

## Fallback to API Token Auth

If OAuth is not enabled (`enabled: false` in config.yaml), the app falls back to API token authentication using the `email` and `api_token` fields.

```yaml
oauth:
  enabled: false  # Falls back to API token auth

jira:
  email: "your-email@example.com"
  api_token: "YOUR_API_TOKEN"
```

## Security Best Practices

1. **Never commit secrets** - Use environment variables or secrets manager
2. **Rotate secrets** - Regularly rotate Client Secret in Atlassian console
3. **Use HTTPS in production** - Ensure `redirect_uri` uses https:// for production
4. **Monitor access** - Check logs for suspicious authentication patterns
5. **Limit scopes** - Only request OAuth scopes that are needed
6. **Token expiry** - Implement token refresh for long-running dashboards

## Environment Variables

You can set OAuth config via environment variables instead of config.yaml:

```bash
$env:OAUTH_CLIENT_ID = "your-client-id"
$env:OAUTH_CLIENT_SECRET = "your-client-secret"
$env:OAUTH_ENABLED = "true"
```

The app will check environment variables first, then fall back to config.yaml.

## Support

For OAuth-related issues:
- Check **Atlassian Developer Console**: https://developer.atlassian.com/console/
- Review **app logs**: Set `LOG_LEVEL=DEBUG` in .env file
- Consult **Atlassian OAuth docs**: https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/
