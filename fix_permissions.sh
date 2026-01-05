#!/bin/bash

# ====================================================
# RecoverAI: Fix IAM Permissions for Cloud SQL
# ====================================================

echo "--> Fetching Project Details..."
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
REGION="us-central1"

# The Default Service Account used by Cloud Run
SERVICE_ACCOUNT="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

echo "--> Service Account: $SERVICE_ACCOUNT"

# 1. GRANT CLOUD SQL CLIENT ROLE
# This is the #1 reason for connection failures!
echo "--> Granting Cloud SQL Client Role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/cloudsql.client"

# 2. REDEPLOY TO PICK UP CHANGES
echo "--> Restarting Cloud Run Service..."
# We just update the service with no changes to force a fresh revision check
gcloud run services update recoverai-backend \
    --region $REGION \
    --update-env-vars RESTART_TRIGGER=$(date +%s)

echo "===================================================="
echo "PERMISSIONS FIXED!"
echo "Please wait 60 seconds, then try 'curl' or refresh your Frontend."
echo "===================================================="
