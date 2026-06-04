# Google Vertex AI Configuration

## Prerequisites
- Google Cloud Platform (GCP) Project
- Vertex AI API enabled
- Service Account with appropriate permissions

## Setup Steps

### 1. Create Service Account
```bash
# Set your project ID
export PROJECT_ID="your-project-id"

# Create service account
gcloud iam service-accounts create edututor-ai \
    --display-name="EduTutor AI Service Account"

# Grant necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:edututor-ai@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:edututor-ai@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.admin"
```

### 2. Create and Download Service Account Key
```bash
gcloud iam service-accounts keys create service_account.json \
    --iam-account=edututor-ai@$PROJECT_ID.iam.gserviceaccount.com
```

Place the `service_account.json` file in the `infrastructure/gcp/` directory.

### 3. Enable Required APIs
```bash
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage-api.googleapis.com
gcloud services enable compute.googleapis.com
```

### 4. Configure Environment
Update your `.env` file with:
```
GCP_PROJECT_ID=your-project-id
VERTEX_API_KEY=<api-key-from-gcp>
```

## Using Vertex AI Models

### Available Models
- `text-bison` - For text generation
- `textembedding-gecko` - For embeddings
- `code-bison` - For code generation

### Model Configuration
Models can be configured in `backend/ai/vertex_client.py`

### Rate Limiting
- Default: 60 requests per minute
- Customize in settings

## Monitoring & Logging
- View logs in Google Cloud Console
- Vertex AI dashboard for model performance
- Cloud Logging for system logs

## Cost Optimization
1. Use batch processing for embeddings
2. Cache frequently requested responses
3. Implement rate limiting
4. Monitor API usage in GCP Console

## Troubleshooting
- Check service account permissions
- Verify API is enabled
- Review GCP project quotas
- Check network connectivity to Google APIs
