# ShieldStream 🛡️

A secure video streaming platform that encrypts video content using Fernet symmetric encryption. Videos are split into 30-second segments, watermarked, and encrypted before storage.

## Features
- 📹 Video upload with invisible watermarking via FFmpeg
- 🔐 Per-segment Fernet encryption
- 🎬 Secure decryption and reassembly for playback
- 🔍 Piracy link scanner
- ☁️ Deployed on Azure via Docker

## Project Structure
```
ShieldStream/
├── api/
│   ├── __init__.py
│   └── app.py          # Flask application
├── static/
│   ├── script.js       # Frontend JS
│   └── style.css       # Styles
├── templates/
│   └── index.html      # Main UI
├── Dockerfile          # Azure container config
├── startup.sh          # Azure App Service startup
├── requirements.txt    # Python dependencies
└── .gitignore
```

## Azure Deployment

### 1. Login
```bash
az login
az group create --name ShieldStreamRG --location eastus
```

### 2. Create Container Registry
```bash
az acr create --resource-group ShieldStreamRG --name shieldstreamacr --sku Basic --admin-enabled true
az acr credential show --name shieldstreamacr
```

### 3. Build & Push Docker Image
```bash
docker login shieldstreamacr.azurecr.io --username shieldstreamacr --password <PASSWORD>
docker build -t shieldstreamacr.azurecr.io/shieldstream:latest .
docker push shieldstreamacr.azurecr.io/shieldstream:latest
```

### 4. Deploy Web App
```bash
az appservice plan create --name ShieldStreamPlan --resource-group ShieldStreamRG --sku B1 --is-linux
az webapp create --resource-group ShieldStreamRG --plan ShieldStreamPlan --name shieldstream-app --deployment-container-image-name shieldstreamacr.azurecr.io/shieldstream:latest
az webapp config appsettings set --resource-group ShieldStreamRG --name shieldstream-app --settings WEBSITES_PORT=8000
```

### 5. Open App
```bash
az webapp browse --resource-group ShieldStreamRG --name shieldstream-app
```

## Health Check
Visit `/health` to verify FFmpeg is available on the server.

## Local Development
```bash
pip install -r requirements.txt
python api/app.py
```
> Requires FFmpeg installed locally: `brew install ffmpeg` (Mac) or `apt install ffmpeg` (Linux)
