# Firebase Setup Guide for SLIM AI

Follow these steps to set up your Firebase project and get the credentials needed for the platform.

## 1. Create a Firebase Project
1.  Go to the [Firebase Console](https://console.firebase.google.com/).
2.  Click **Add project** and follow the prompts to create a new project (e.g., "slim-ai-lake").

## 2. Enable Firestore Database
1.  In the Firebase sidebar, click **Build** > **Firestore Database**.
2.  Click **Create database**.
3.  Choose a location and start in **Test mode** (you can update rules later).
4.  Click **Create**.

## 3. Generate Service Account Key
1.  Click the **Settings (gear icon)** next to "Project Overview" and select **Project settings**.
2.  Go to the **Service accounts** tab.
3.  Click **Generate new private key**.
4.  A JSON file will download. **Rename this file to `firebase-key.json`**.
5.  Move `firebase-key.json` to the root directory of your project: `g:\hacky4\New folder\simats---aqua\`.

## 4. Update Environment Variables
Open your `.env` file and update the following:

```env
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_SERVICE_ACCOUNT_PATH=firebase-key.json
```

> [!WARNING]
> Keep your `firebase-key.json` private. It is already added to `.gitignore` to prevent it from being uploaded.
