# 🏃 Simple Jira Cloud Streamlit Dashboard

A simple Streamlit application to connect with Jira Cloud and display project and sprint information.

## ✨ Features

- **Jira Cloud Integration**: Connect securely using API token authentication
- **Project Information**: Display project name, key, and description
- **Active Sprint Details**: Show current sprint name, start date, and end date
- **Sidebar Navigation**: Easy navigation between different dashboard pages
- **Manual Refresh**: Button to manually refresh data from Jira
- **Error Handling**: Clear error messages for connection issues
- **Placeholder Pages**: Framework for future features (Tech Debt, Sprint Metrics, Custom Reports)

## 📋 Prerequisites

- Python 3.8 or higher
- Jira Cloud account with API access
- Internet connection to reach Jira Cloud

## 🔧 Setup Instructions

### Step 1: Install Dependencies

Navigate to the project directory and install required packages:

```bash
pip install -r requirements.txt
```

### Step 2: Get Your Jira API Token

1. Visit: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **Create API token**
3. Give it a name (e.g., "Streamlit Dashboard")
4. Copy the generated token (you'll need this for config.yaml)
5. **Keep this token secure** - treat it like a password

**Important**: Use the API token, NOT your Jira password

### Step 3: Find Your Board ID

1. Log in to your Jira Cloud instance
2. Navigate to the project board you want to track
3. Look at the URL in your browser. It will look something like:
   ```
   https://your-domain.atlassian.net/software/c/projects/MYPROJECT/boards/1234
   ```
4. The number after `/boards/` is your **Board ID** (in this example: `1234`)

### Step 4: Configure with config.yaml OR Environment Variables

**Option A: config.yaml (Development)**

Open `config.yaml` and fill in your Jira details:

```yaml
jira:
  url: "https://your-domain.atlassian.net"        # Your Jira Cloud URL
  email: "your-email@example.com"                  # Your Jira account email
  api_token: "your-api-token-here"                 # API token from Step 2
  project_key: "MYPROJECT"                         # Your project key (uppercase)
  board_id: 1234                                   # Board ID from Step 3
```

**Option B: Environment Variables (Recommended for Production)**

Create a `.env` file (or set environment variables):

```env
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_TOKEN=your-api-token-here
JIRA_PROJECT_KEY=MYPROJECT
JIRA_BOARD_ID=1234
LOG_LEVEL=WARNING
CACHE_TTL=300
```

Environment variables take priority over `config.yaml`


### Step 5: Run the Application

Start the Streamlit app:

```bash
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`

## 🚀 Usage

### Home Page
- Displays project information (name, key, description)
- Shows active sprint details (name, start date, end date)
- "Refresh" button to manually reload data from Jira

### Navigation Menu (Sidebar)
- **Home**: Current page with project and sprint info
- **Tech Debt Dashboard**: Placeholder for future development
- **Sprint Metrics**: Placeholder for future development
- **Custom Reports**: Placeholder for future development

## 🔐 Security Best Practices

1. **Never commit credentials**: Don't push `config.yaml` with real credentials to version control
2. **Use .gitignore**: Add `config.yaml` to `.gitignore` to prevent accidental commits
3. **API Token Security**: Treat API tokens like passwords - keep them confidential
4. **Regenerate if compromised**: If you suspect your token is exposed, regenerate it immediately

### Suggested .gitignore entry:
```
config.yaml
.streamlit/
__pycache__/
*.pyc
.env
```

## 🐛 Troubleshooting

### Connection Failed Error
- Verify your Jira URL is correct (should end with `.atlassian.net`)
- Check that the email address is correct
- Ensure API token is valid and hasn't expired
- Try regenerating the API token

### Project Not Found
- Verify the project key is correct (visible in Jira as uppercase)
- Ensure you have access to this project in Jira

### No Active Sprint Found
- Create a sprint in your Jira board
- Or check that the Board ID in config.yaml is correct

### Authentication Errors
- API token may have expired - regenerate at https://id.atlassian.com/manage-profile/security/api-tokens
- Verify email address hasn't changed

## � Deployment

This app is production-ready and can be deployed to various platforms:

### Quick Deployment (Recommended)

**Docker Deployment** (Requires Docker):
```bash
cp .env.example .env
# Edit .env with your credentials
docker-compose up -d
# Access at http://localhost:8501
```

**Streamlit Cloud** (Zero DevOps):
1. Push code to GitHub (`.env` and `config.yaml` in `.gitignore`)
2. Go to https://streamlit.io/cloud
3. Connect your repo and add environment variables
4. App deploys automatically!

**Manual VPS/Server**:
See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions including:
- Manual Python installation
- Systemd service setup
- Nginx reverse proxy configuration
- Security hardening

### Deployment Features
✅ Environment variable support (.env files)
✅ Docker & Docker Compose ready
✅ Production-grade error handling
✅ Connection retry logic
✅ Request timeouts
✅ Configurable logging
✅ Non-root container execution
✅ Health checks included

For detailed deployment instructions, see **[DEPLOYMENT.md](DEPLOYMENT.md)**

## 📦 Project Structure

```
project/
├── app.py                     # Main Streamlit application
├── config.example.yaml        # Configuration template
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker containerization
├── docker-compose.yml        # Docker Compose orchestration
├── .streamlit/config.toml    # Streamlit production config
├── README.md                 # This file
├── DEPLOYMENT.md             # Deployment guide
└── .gitignore               # Prevents committing secrets
```

**Note**: `config.yaml` and `.env` are in `.gitignore` for security


## 🔄 Future Enhancements

The placeholder pages are ready for these features:
- **Tech Debt Dashboard**: Filter and track accumulated technical debt
- **Sprint Metrics**: Velocity trends, burndown charts, team performance
- **Custom Reports**: Custom JQL queries, exportable reports, issue breakdowns

## 💡 Tips

- The app caches the Jira connection, so it only connects once per session
- Use the Refresh button to get the latest data from Jira
- For development, run with: `streamlit run app.py --logger.level=debug`

## 📚 Additional Resources

- [Jira Cloud API Documentation](https://developer.atlassian.com/cloud/jira/rest/v3/)
- [Jira Python Library (jira-python)](https://jira.readthedocs.io/)
- [Streamlit Documentation](https://docs.streamlit.io/)

## ⚠️ Limitations

- Displays only the current active sprint
- Does not support Jira Server or Jira Data Center (Cloud only)
- Requires internet connection to Jira Cloud

## 📝 License

This project is provided as-is for managing Jira dashboards.

---

**Happy dashboard building! 🎉**
