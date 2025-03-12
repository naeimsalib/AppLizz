# Email Integration Setup Guide

This guide provides step-by-step instructions for setting up API credentials for each email service supported by JobJourney.

## Table of Contents

1. [Google (Gmail) Setup](#google-gmail-setup)
2. [Yahoo Mail Setup](#yahoo-mail-setup)
3. [Microsoft (Outlook) Setup](#microsoft-outlook-setup)
4. [Configuring Your Application](#configuring-your-application)

## Google (Gmail) Setup

### Step 1: Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top of the page
3. Click "New Project"
4. Enter a name for your project (e.g., "JobJourney")
5. Click "Create"

### Step 2: Enable the Gmail API

1. Select your newly created project
2. In the left sidebar, navigate to "APIs & Services" > "Library"
3. Search for "Gmail API"
4. Click on "Gmail API" in the results
5. Click "Enable"

### Step 3: Configure OAuth Consent Screen

1. In the left sidebar, navigate to "APIs & Services" > "OAuth consent screen"
2. Select "External" as the user type (unless you have a Google Workspace account)
3. Click "Create"
4. Fill in the required information:
   - App name: "JobJourney"
   - User support email: Your email address
   - Developer contact information: Your email address
5. Click "Save and Continue"
6. On the "Scopes" page, click "Add or Remove Scopes"
7. Add the scope: `https://www.googleapis.com/auth/gmail.readonly`
8. Click "Save and Continue"
9. On the "Test users" page, click "Add Users"
10. Add your email address
11. Click "Save and Continue"
12. Review your settings and click "Back to Dashboard"

### Step 4: Create OAuth 2.0 Credentials

1. In the left sidebar, navigate to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Select "Web application" as the application type
4. Name: "JobJourney Web Client"
5. Add authorized JavaScript origins:
   - `http://localhost:3000`
   - `http://127.0.0.1:3000`
6. Add authorized redirect URIs:
   - `http://localhost:3000/gmail_callback`
   - `http://127.0.0.1:3000/gmail_callback`
7. Click "Create"
8. A popup will display your client ID and client secret. Save these values.

## Yahoo Mail Setup

### Step 1: Create a Yahoo Developer Account

1. Go to the [Yahoo Developer Network](https://developer.yahoo.com/)
2. Click "Sign In" and log in with your Yahoo account (or create one if needed)

### Step 2: Create a New App

1. Go to the [Yahoo Developer Dashboard](https://developer.yahoo.com/apps/)
2. Click "Create an App"
3. Fill in the required information:
   - Application Name: "JobJourney"
   - Description: "Job application tracking app"
   - Home Page URL: `http://localhost:3000`
   - Callback Domain: `localhost`
4. Under "API Permissions", select:
   - "Yahoo Social Directory" - Read
   - "Yahoo Mail" - Read
5. Click "Create App"

### Step 3: Get Your Credentials

1. After creating the app, you'll be taken to the app details page
2. Note your "Client ID" and "Client Secret"
3. Under "Redirect URI(s)", click "Add" and enter:
   - `http://localhost:3000/yahoo_callback`
4. Click "Save"

## Microsoft (Outlook) Setup

### Step 1: Register an Application in Azure

1. Go to the [Azure Portal](https://portal.azure.com/)
2. Sign in with your Microsoft account
3. Search for "Azure Active Directory" and select it
4. In the left sidebar, click on "App registrations"
5. Click "New registration"
6. Fill in the required information:
   - Name: "JobJourney"
   - Supported account types: "Accounts in any organizational directory and personal Microsoft accounts"
   - Redirect URI: Select "Web" and enter `http://localhost:3000/outlook_callback`
7. Click "Register"

### Step 2: Configure API Permissions

1. In your newly created app, click on "API permissions" in the left sidebar
2. Click "Add a permission"
3. Select "Microsoft Graph"
4. Click "Delegated permissions"
5. Search for and select the following permissions:
   - `Mail.Read`
   - `offline_access` (for refresh tokens)
6. Click "Add permissions"

### Step 3: Get Your Credentials

1. In the left sidebar, click on "Overview"
2. Note your "Application (client) ID"
3. Click on "Certificates & secrets" in the left sidebar
4. Under "Client secrets", click "New client secret"
5. Add a description and select an expiration period
6. Click "Add"
7. Note the "Value" of the client secret (you won't be able to see it again)

## Configuring Your Application

After obtaining your API credentials, you need to add them to your `.env` file:

```
# Google OAuth Configuration (for Gmail integration)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3000/gmail_callback

# Yahoo OAuth Configuration (for Yahoo Mail integration)
YAHOO_CLIENT_ID=your-yahoo-client-id
YAHOO_CLIENT_SECRET=your-yahoo-client-secret
YAHOO_REDIRECT_URI=http://localhost:3000/yahoo_callback

# Microsoft OAuth Configuration (for Outlook integration)
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret
MICROSOFT_REDIRECT_URI=http://localhost:3000/outlook_callback
```

Replace the placeholder values with your actual credentials.

## Security Considerations

- Never commit your `.env` file to version control
- Keep your client secrets secure
- For production, use HTTPS for all redirect URIs
- Regularly rotate your client secrets
- Only request the minimum permissions needed
