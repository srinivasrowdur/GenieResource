# Firebase Setup Guide

This guide explains how to set up Firebase credentials for the Resource Management Agent.

## Getting Firebase Credentials

1. Go to the [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select an existing one
3. Navigate to Project Settings (gear icon) > Service Accounts
4. Click "Generate New Private Key"
5. Save the downloaded JSON file as `firebase_credentials.json` in the project root directory

## Setting Up the Credentials

You have two options to configure your Firebase credentials:

### Option 1: Place credentials in the project root (recommended)
Simply save the downloaded JSON file as `firebase_credentials.json` in the project root directory.

### Option 2: Use an environment variable
Set the environment variable to point to your credentials file:

```bash
export FIREBASE_CREDENTIALS_PATH="/absolute/path/to/firebase_credentials.json"
```

## Creating Firebase Database Structure

The application requires a specific Firestore database structure with two collections:

### 1. Employees Collection

In the Firebase Console, go to Firestore Database and create a collection called `employees`.

Add employee documents with the following fields:
- `name`: string (e.g., "John Doe")
- `employee_number`: string (e.g., "EMP123")
- `location`: string (e.g., "London")
- `rank`: map with field `official_name`: string (e.g., "Senior Consultant")
- `skills`: array of strings (e.g., ["python", "machine learning", "aws"])

#### Sample Employee Document

```json
{
  "name": "John Doe",
  "employee_number": "EMP123",
  "location": "London", 
  "rank": {
    "official_name": "Senior Consultant"
  },
  "skills": ["python", "machine learning", "aws"]
}
```

### 2. Availability Collection

Create another collection called `availability`.

1. Create documents with IDs matching employee numbers (e.g., "EMP123")
2. For each availability document, create a subcollection called `weeks`
3. In the `weeks` subcollection, add documents for each week with:
   - `week_number`: number (e.g., 1)
   - `status`: string (e.g., "available", "partial", "unavailable")
   - `hours`: number (e.g., 40)
   - `notes`: string (optional, e.g., "Working on Project X")

#### Sample Availability Structure

```
availability (collection)
└── EMP123 (document)
    └── weeks (subcollection)
        ├── week1 (document)
        │   ├── week_number: 1
        │   ├── status: "available"
        │   ├── hours: 40
        │   └── notes: "Working on Project X"
        └── week2 (document)
            ├── week_number: 2
            ├── status: "partial"
            ├── hours: 20
            └── notes: "Training"
```

## Security Notes

- Never commit your actual Firebase credentials to version control
- Keep your credentials file secure
- Use appropriate Firebase security rules
- Consider using environment variables for sensitive data

## Troubleshooting

If you encounter Firebase connection issues:

- Verify your credentials file is correctly formatted with all required fields
- Check that the file is in the correct location or environment variable is set correctly
- Ensure your Firebase project is properly configured with Firestore enabled
- Check your network connection and firewall settings
- Verify that you have the appropriate permissions in the Firebase project

For more help, refer to the [Firebase Admin SDK documentation](https://firebase.google.com/docs/admin/setup) 