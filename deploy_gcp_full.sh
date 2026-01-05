#!/bin/bash

# ====================================================
# RecoverAI: Full Cloud Deployment Script (GCP)
# ====================================================
# This script provisions:
# 1. Cloud SQL (PostgreSQL Database)
# 2. Cloud Run (Python Backend)
# 3. Connects them securely
# ====================================================

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
DB_INSTANCE_NAME="recoverai-db-instance"
DB_NAME="recoverai_prod"
DB_USER="admin"
DB_PASS="SuperSecretPass123!" # Change this in production!

echo "Using Project: $PROJECT_ID"

# 1. ENABLE GOOGLE CLOUD APIS
echo "--> Enabling APIs..."
gcloud services enable run.googleapis.com sqladmin.googleapis.com cloudbuild.googleapis.com aiplatform.googleapis.com

# 2. CREATE CLOUD SQL INSTANCE (The Persistent Database)
echo "--> Creating Cloud SQL Instance (This takes ~5 mins)..."
gcloud sql instances create $DB_INSTANCE_NAME \
    --database-version=POSTGRES_14 \
    --cpu=1 \
    --memory=3840MiB \
    --region=$REGION \
    --root-password=$DB_PASS

# 3. CREATE DATABASE & USER
echo "--> configuring Database Schema..."
gcloud sql databases create $DB_NAME --instance=$DB_INSTANCE_NAME
gcloud sql users create $DB_USER --instance=$DB_INSTANCE_NAME --password=$DB_PASS

# 4. GET CONNECTION STRING
# Format: PROJECT_ID:REGION:INSTANCE_NAME
INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE_NAME --format="value(connectionName)")
echo "--> Database Connection Name: $INSTANCE_CONNECTION_NAME"

# 5. DEPLOY BACKEND TO CLOUD RUN (The Compute)
echo "--> Deploying Backend to Cloud Run..."
gcloud run deploy recoverai-backend \
    --source . \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --add-cloudsql-instances $INSTANCE_CONNECTION_NAME \
    --set-env-vars "DATABASE_URL=postgresql+psycopg2://$DB_USER:$DB_PASS@/$DB_NAME?host=/cloudsql/$INSTANCE_CONNECTION_NAME"

echo ====================================================
echo "DEPLOYMENT COMPLETE!"
echo "Backend is running on Cloud Run."
echo "Database is running on Cloud SQL."
echo "They are securely linked via Unix Socket."
echo ====================================================
