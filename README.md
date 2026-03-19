# FastAPI on GCP Cloud Run 多環境部署

FastAPI 應用程式部署至 GCP Cloud Run，支援 DEV / PROD 兩套獨立環境，透過 GitHub Actions 自動化 CI/CD。

## 架構

```
git push develop  →  GitHub Actions  →  Cloud Build  →  Cloud Run (DEV)
git push main     →  GitHub Actions  →  Cloud Build  →  Cloud Run (PROD)
```

## 環境規格

| 項目 | DEV | PROD |
|------|-----|------|
| Cloud Run 服務名稱 | `fastapi-service-dev` | `fastapi-service-prod` |
| CPU | 1 | 2 |
| Memory | 256Mi | 1Gi |
| 最小實例數 | 0 | 1 |
| 最大實例數 | 3 | 20 |
| 環境變數 `ENV` | `development` | `production` |

## 專案結構

```
├── .github/workflows/deploy.yml       # CI/CD Workflow
├── app/
│   ├── config.py                      # 環境設定
│   └── main.py                        # FastAPI 應用
├── tests/test_main.py                 # 單元測試
├── environments/
│   ├── cloudbuild.dev.yaml            # DEV Cloud Build 設定
│   └── cloudbuild.prod.yaml           # PROD Cloud Build 設定
├── Dockerfile                         # 多階段 build
└── requirements.txt
```

## API 端點

| 端點 | 說明 |
|------|------|
| `GET /` | 回傳環境資訊 |
| `GET /health` | Health check |

## 本地開發

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

## 本地測試

```bash
pytest tests/ -v
```

## 部署前置作業

### 1. 安裝 gcloud CLI

```bash
brew install --cask google-cloud-sdk
gcloud auth login
```

### 2. 建立 GCP 基礎建設

```bash
export PROJECT_ID="your-project-id"
export REGION="asia-east1"
export GITHUB_REPO="duncan60/gcp-cloudrun-fastapi"

# 啟用 API
gcloud config set project $PROJECT_ID
gcloud services enable cloudbuild.googleapis.com run.googleapis.com \
  artifactregistry.googleapis.com compute.googleapis.com iam.googleapis.com

# Artifact Registry
gcloud artifacts repositories create fastapi-repo \
  --repository-format=docker --location=$REGION

# Service Account
gcloud iam service-accounts create github-actions-sa \
  --display-name="GitHub Actions Deploy SA"
export SA_EMAIL="github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com"
for ROLE in roles/cloudbuild.builds.editor roles/run.admin roles/artifactregistry.writer roles/iam.serviceAccountUser roles/storage.admin; do
  gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:${SA_EMAIL}" --role="$ROLE"
done

# Workload Identity Federation
gcloud iam workload-identity-pools create "github-pool" --location="global"
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --location="global" --workload-identity-pool="github-pool" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"
export POOL_NAME=$(gcloud iam workload-identity-pools describe "github-pool" --location="global" --format="value(name)")
gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${POOL_NAME}/attribute.repository/${GITHUB_REPO}"

# 取得 WIF Provider 路徑（填入 deploy.yml）
gcloud iam workload-identity-pools providers describe "github-provider" \
  --location="global" --workload-identity-pool="github-pool" --format="value(name)"

# 建立 Cloud Run 服務（placeholder）
gcloud run deploy fastapi-service-dev \
  --image=us-docker.pkg.dev/cloudrun/container/hello \
  --region=$REGION --allow-unauthenticated --cpu=1 --memory=256Mi --min-instances=0 --max-instances=3

gcloud run deploy fastapi-service-prod \
  --image=us-docker.pkg.dev/cloudrun/container/hello \
  --region=$REGION --allow-unauthenticated --cpu=2 --memory=1Gi --min-instances=1 --max-instances=20
```

### 3. 更新 `.github/workflows/deploy.yml`

```yaml
PROJECT_ID: your-project-id
WIF_PROVIDER: 'projects/xxx/locations/global/workloadIdentityPools/github-pool/providers/github-provider'
SA_EMAIL: 'github-actions-sa@your-project-id.iam.gserviceaccount.com'
```

## 開發流程

```bash
# 1. 從 develop 建立 feature branch
git checkout develop
git checkout -b feature/your-feature

# 2. 開發完成，推上去建立 PR → develop
git push origin feature/your-feature

# 3. Merge 到 develop → 自動部署 DEV

# 4. DEV 驗證通過後，建立 PR: develop → main

# 5. Merge 到 main → 自動部署 PROD
```

## Rollback

```bash
# 查看版本列表
gcloud run revisions list --service=fastapi-service-dev --region=asia-east1

# 回滾到指定版本
gcloud run services update-traffic fastapi-service-dev \
  --region=asia-east1 \
  --to-revisions=fastapi-service-dev-XXXXX=100
```
