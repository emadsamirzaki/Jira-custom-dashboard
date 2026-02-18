# OAuth Authentication Troubleshooting Guide

## Error: "authorization_code is invalid"

This is the most common OAuth error. It means the credentials or redirect URI don't match between your Jira app registration and the application configuration.

### ✅ How to Fix

Follow these steps **exactly**:

#### 1. Check Your Redirect URI

Go to [Atlassian Developer Console](https://developer.atlassian.com/console/myapps/):

1. Click your app (or create a new one if you don't have one)
2. Go to **Settings** → **OAuth 2.0 incoming (3LO)**
3. Find **Redirect URIs** section
4. Check if `http://localhost:8501` is listed there
5. **Important:** It must match EXACTLY:
   - Must be `http://` (lowercase)
   - Must be `localhost:8501` (not 127.0.0.1)
   - No trailing slash

If missing or different, update it:
- Delete the old redirect URI
- Add: `http://localhost:8501`
- Save changes

#### 2. Verify Your Credentials

In Atlassian Developer Console, under **OAuth 2.0 incoming (3LO)**, copy:
- **Client ID** 
- **Client Secret** (click "New secret" if needed)

#### 3. Update Your config.yaml

```yaml
oauth:
  enabled: true
  client_id: "PASTE_YOUR_CLIENT_ID_HERE"
  client_secret: "PASTE_YOUR_CLIENT_SECRET_HERE"
  redirect_uri: "http://localhost:8501"
  scope: "read:me read:jira-work read:jira-user offline_access"
  auth_url: "https://auth.atlassian.com/authorize"
  token_url: "https://auth.atlassian.com/oauth/token"
  resource_url: "https://api.atlassian.com/me"
```

**⚠️ IMPORTANT:**
- Don't use placeholder text like `"YOUR_CLIENT_ID_HERE"`
- Copy exact values from Atlassian Console
- Check for extra spaces or quotes

#### 4. Restart the App

```bash
python -m streamlit run app.py
```

#### 5. Test Login

1. Click "Login with Jira" button
2. You should be redirected to Atlassian login
3. Log in with your Atlassian account
4. You'll be redirected back to the dashboard

### 🔍 Debugging Steps

If you still get the error:

1. **Check browser console** for any error messages
2. **Verify Jira is accessible**: Go to https://wkengineering.atlassian.net in your browser
3. **Try incognito mode** to clear browser cache
4. **Check app logs** - Streamlit shows detailed error messages in the terminal

### 📋 Checklist

- [ ] Redirect URI exactly matches: `http://localhost:8501`
- [ ] Client ID and Client Secret copied from Atlassian Console
- [ ] config.yaml updated with real credentials (not placeholders)
- [ ] No extra spaces or typos in credentials
- [ ] App restarted after config changes
- [ ] Browser cache cleared (or use incognito mode)

### 🆘 Still Not Working?

1. **Delete client secret and create a new one:**
   - Atlassian Console → Your App → OAuth → Delete old secret → Create new secret
   
2. **Create a new OAuth app:**
   - Atlassian Developer Console → New app
   - Configure redirect URI: `http://localhost:8501`
   - Copy new credentials to config.yaml

3. **Check firewall/proxy:**
   - Make sure `localhost:8501` is accessible
   - Not behind a corporate proxy that might interfere with OAuth

## Microsoft Entra ID (Azure AD) Authentication

### Error: "authorization_code is invalid" (Microsoft)

If you're logging in with Microsoft and get this error, follow these steps:

#### 1. Check Redirect URI in Azure

Go to [Azure Portal - App Registrations](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade):

1. Find your app registration
2. Click **Authentication** in the left sidebar
3. Under **Platform configurations**, find **Web**
4. Check **Redirect URIs** - must contain exactly: `http://localhost:8501`
5. If missing or different:
   - Click **Add URI**
   - Add: `http://localhost:8501`
   - Click **Save**

#### 2. Verify Client Secret

1. In Azure Portal, click **Certificates & secrets**
2. Under **Client secrets**, check if your secret has expired
3. If expired or missing:
   - Click **+ New client secret**
   - Set expiration (e.g., 24 months)
   - Click **Add**
   - **Copy the secret VALUE** (not the ID)

#### 3. Update config.yaml

```yaml
microsoft:
  enabled: true
  client_id: "PASTE_FROM_AZURE_PORTAL_OVERVIEW"  # Copy from Azure Overview tab
  client_secret: "PASTE_NEW_SECRET_VALUE_HERE"   # Copy from Certificates & secrets
  tenant_id: "PASTE_FROM_AZURE_PORTAL_OVERVIEW"  # Copy from Azure Overview tab (Tenant ID)
  redirect_uri: "http://localhost:8501"          # Must match Azure redirect URI
  scope: "openid profile email User.Read"
```

**To find these values in Azure:**
- Go to **Overview** tab
- **Application (client) ID** → copy to `client_id`
- **Directory (tenant) ID** → copy to `tenant_id`

#### 4. Restart Your App

```bash
python -m streamlit run app.py
```

#### 5. Test Login

1. Click **Login with Microsoft**
2. Log in with your Microsoft account
3. You should be redirected back to the dashboard

### Microsoft Authentication Checklist

- [ ] Redirect URI in Azure includes exactly: `http://localhost:8501`
- [ ] Client ID copied from Azure Portal (Application ID)
- [ ] Client Secret created and copied (not the secret ID)
- [ ] Tenant ID copied from Azure Portal (Directory ID)
- [ ] config.yaml updated with all values
- [ ] No placeholder text remaining ("PASTE_FROM_AZURE...", "YOUR_...", etc.)
- [ ] App restarted after config changes
- [ ] Browser cache cleared or using incognito mode

### Still Having Issues?

1. **Try creating a new app registration:**
   - Azure Portal → App registrations → New registration
   - Name: "Jira Dashboard Local"
   - Supported account types: "Accounts in this organizational directory only"
   - Redirect URI: `http://localhost:8501`
   - Click Register
   - Copy new Client ID and Tenant ID
   - Create new Client Secret
   - Update config.yaml with new values

2. **Check Application Permissions:**
   - Azure Portal → Your App → API permissions
   - Should have: **User.Read** (Microsoft Graph)
   - If missing: Click **Add a permission** → **Microsoft Graph** → **Delegated permissions** → Check **User.Read** → **Add permissions**

3. **Verify Tenant ID:**
   - Make sure you're using the correct tenant ID for your organization
   - Go to Azure Portal → Azure AD → Properties → Tenant ID

## For Production Deployment

When deploying to production, update both OAuth providers:

```yaml
oauth:
  redirect_uri: "https://your-production-domain.com"
  # Also add this to Atlassian Console OAuth Redirect URIs

microsoft:
  redirect_uri: "https://your-production-domain.com"
  # Also add this to Azure Portal App Registration Redirect URIs
```

Then register redirect URIs in:
- **Atlassian Developer Console** for Jira OAuth
- **Azure Portal** for Microsoft OAuth
