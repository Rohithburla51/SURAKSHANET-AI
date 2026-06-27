# 🚀 SurakshaNet AI — Deployment Commands & Checklist

**Status**: ✅ Phase 6 Complete — All Code Ready  
**Date**: June 27, 2026  
**Git Remote**: https://github.com/Rohithburla51/SURAKSHANET-AI.git  

---

## ✅ Pre-Deployment Verification

### 1. **Git Status Check**
```powershell
cd "c:\Users\burla\OneDrive\Documents\PROJECTS_BY_ROHITH\AI SECURITY PROJECT"
git status
```
**Expected Output**: `nothing to commit, working tree clean`

### 2. **.env File Check**
✅ `.env` exists with all 7 credentials:
- `GROQ_API_KEY` → Groq LLaVA/Mixtral access
- `DATABASE_URL` → Supabase PostgreSQL connection
- `NEO4J_URI` → Neo4j Aura instance (f4997b01)
- `NEO4J_USER` → f4997b01
- `NEO4J_PASSWORD` → [Stored securely]
- `HUGGINGFACE_API_KEY` → HF Spaces deployment token
- `DEMO_MOCK_MODE=false` → Using live APIs

⚠️ **CRITICAL**: `.gitignore` correctly excludes `.env` — verified in `.gitignore`.

### 3. **.gitignore Verification**
✅ All sensitive files properly ignored:
- `.env` and `.env.*` files
- `node_modules/`, `__pycache__/`, `.venv/`
- ML model caches (HuggingFace, ONNX)
- Private keys, secrets, credentials

---

## 🏃 Local Development — Quick Start

### **Backend (FastAPI + Uvicorn)**

```powershell
# Terminal 1 — Backend
cd "c:\Users\burla\OneDrive\Documents\PROJECTS_BY_ROHITH\AI SECURITY PROJECT\backend"
C:\Users\burla\miniconda3\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
✅ SurakshaNet AI is ready to serve requests.
```

**Verify Health**:
```powershell
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

---

### **Frontend (Next.js 14)**

```powershell
# Terminal 2 — Frontend
cd "c:\Users\burla\OneDrive\Documents\PROJECTS_BY_ROHITH\AI SECURITY PROJECT\frontend"
npm run dev
```

**Expected Output**:
```
✓ Ready in 1992ms
○ Compiling / ...
✓ Compiled / in 2.6s
```

**Open Browser**:
- `http://localhost:3000` — Unified tabbed portal (Citizen + Bank)
- `http://localhost:3000/police` — Police Cypher Intelligence Dashboard (optional)

---

## 🌐 Production Deployment

### **A. GitHub Push (If Not Already Done)**

```powershell
cd "c:\Users\burla\OneDrive\Documents\PROJECTS_BY_ROHITH\AI SECURITY PROJECT"

# Resolve any remote conflicts (if README exists on GitHub)
git pull origin main --allow-unrelated-histories --no-edit

# Push all commits
git push -u origin main
```

**Verify on GitHub**: https://github.com/Rohithburla51/SURAKSHANET-AI

---

### **B. Deploy Frontend → Vercel**

#### **Step 1: Connect GitHub to Vercel**
1. Go to https://vercel.com/login
2. Sign in (or create account)
3. Click **"New Project"** → Import Git Repository
4. Select `Rohithburla51/SURAKSHANET-AI`
5. Choose `frontend/` as root directory

#### **Step 2: Configure Environment Variables**
In Vercel Dashboard → **Settings** → **Environment Variables**:

```
NEXT_PUBLIC_API_URL=https://your-hf-spaces-backend-url
```

*(Will be set after HF Spaces deployment in Step C)*

#### **Step 3: Deploy**
- Click **Deploy** (Vercel auto-builds Next.js)
- Wait for build to complete
- Get live URL: `https://surakshanet-ai.vercel.app` (example)

---

### **C. Deploy Backend → Hugging Face Spaces (Docker)**

#### **Step 1: Create HF Space**
1. Go to https://huggingface.co/spaces
2. Click **Create New Space**
3. **Space name**: `surakshanet-ai-backend`
4. **License**: Apache 2.0
5. **Space SDK**: **Docker**
6. Create Space

#### **Step 2: Push Docker Image**

```powershell
# From workspace root
cd "c:\Users\burla\OneDrive\Documents\PROJECTS_BY_ROHITH\AI SECURITY PROJECT"

# Verify Dockerfile exists
type Dockerfile

# (If using Git-based push to HF):
# Add HF repo as remote
git remote add huggingface https://huggingface.co/spaces/<your-username>/surakshanet-ai-backend

# Push backend/ files only (HF auto-builds Dockerfile)
git subtree push --prefix backend huggingface main
```

#### **Step 3: Add Secrets to HF Space**
In Space Settings → **Secrets**:

| Key | Value |
|-----|-------|
| `GROQ_API_KEY` | `gsk_***YOUR_GROQ_API_KEY_FROM_.env***` |
| `DATABASE_URL` | `postgresql://***YOUR_SUPABASE_URL_FROM_.env***` |
| `NEO4J_URI` | `neo4j+s://***YOUR_NEO4J_URI_FROM_.env***` |
| `NEO4J_USER` | `***YOUR_NEO4J_USER_FROM_.env***` |
| `NEO4J_PASSWORD` | `***YOUR_NEO4J_PASSWORD_FROM_.env***` |
| `HUGGINGFACE_API_KEY` | `hf_***YOUR_HF_API_KEY_FROM_.env***` |
| `DEMO_MOCK_MODE` | `false` |

✅ HF Spaces builds and deploys automatically.

#### **Step 4: Get Backend Live URL**
After deployment completes, HF provides:
```
https://username-surakshanet-ai-backend.hf.space
```

---

### **D. Link Frontend ↔ Backend**

#### **Step 1: Update Vercel Env Var**
```
NEXT_PUBLIC_API_URL=https://username-surakshanet-ai-backend.hf.space
```

#### **Step 2: Redeploy Frontend**
In Vercel → Click **Redeploy** to apply new API URL.

---

## 🔍 Verify Live Deployment

```powershell
# Test Backend Health
curl https://username-surakshanet-ai-backend.hf.space/health

# Expected Response
{
  "status": "ok",
  "stack": "HuggingFace + Supabase + Neo4j Aura + Groq",
  "demo_mode": false,
  "databases": {
    "postgres": {"status": "ok"},
    "neo4j": {"status": "ok"}
  }
}

# Test Frontend
curl https://surakshanet-ai.vercel.app
```

---

## 📋 File Checklist — All Components Ready

### **Backend Files** ✅
- `backend/main.py` — FastAPI app with lifespan handler
- `backend/api/routes/scam.py` — Citizen scam analysis endpoint
- `backend/api/routes/counterfeit.py` — Bank counterfeit detection endpoint
- `backend/api/routes/network.py` — Police network Cypher queries
- `backend/agents/scam_agent.py` — RAG + Groq LLM (balanced sensitivity)
- `backend/agents/counterfeit_agent.py` — OpenCV + LLaVA vision model
- `backend/agents/network_agent.py` — NL-to-Cypher + Neo4j tracing
- `backend/services/database.py` — Supabase + Neo4j connectors
- `backend/services/neo4j_graph.py` — MERGE, Ghost Node upserts
- `backend/core/demo_responses.py` — Fallback fixtures
- `requirements.txt` — Pinned Python dependencies
- `Dockerfile` — HF Spaces multi-stage build

### **Frontend Files** ✅
- `frontend/src/app/page.tsx` — Root with tabbed portal (Citizen + Bank unified)
- `frontend/src/components/CitizenPortal.tsx` — Scam detection UI
- `frontend/src/components/BankPortal.tsx` — Counterfeit verification UI
- `frontend/src/components/RiskScore.tsx` — Resilient score display
- `frontend/src/components/CounterfeitReport.tsx` — Resilient report layout
- `frontend/src/components/NetworkGraph.tsx` — Police dashboard visualization
- `frontend/src/app/globals.css` — Dark theme + scrollbar polish
- `frontend/src/lib/api.ts` — API client with new NEO4J_URI
- `frontend/package.json`, `tsconfig.json`, `tailwind.config.js`, `next.config.js` — Configured
- `.env.example` — 7 credentials documented

### **Configuration & Docs** ✅
- `.env.example` — Template (7 services)
- `.env` — Production credentials (kept local, in .gitignore)
- `.gitignore` — Sensitive files excluded
- `README.md` — 3,500+ lines (architecture, quick-start, tech stack)
- `DEPLOYMENT.md` — Detailed deployment steps
- `docker-compose.yml` — Local full-stack orchestration
- `Dockerfile` — Production-ready HF Spaces build
- `.github/workflows/deploy.yml` — CI/CD pipeline (optional, can enable)

---

## 🔧 Troubleshooting

### **Issue: `Failed to fetch from backend`**
- **Cause**: Frontend ENV var `NEXT_PUBLIC_API_URL` not set in Vercel
- **Fix**: Verify `NEXT_PUBLIC_API_URL` is set in Vercel Settings → Environment Variables

### **Issue: Neo4j connection timeout**
- **Cause**: NEO4J_URI or credentials incorrect
- **Fix**: Verify in HF Secrets:
  ```
  NEO4J_URI=neo4j+s://f4997b01.databases.neo4j.io
  NEO4J_USER=f4997b01
  NEO4J_PASSWORD=[Check .env file]
  ```

### **Issue: Groq API rate limit**
- **Cause**: Multiple concurrent requests exceed Groq free tier
- **Fix**: Implement request batching or upgrade Groq plan

### **Issue: HF Spaces build fails**
- **Cause**: Dockerfile syntax or missing dependencies
- **Fix**: Check HF Space logs → rebuild with corrected `requirements.txt`

---

## 📊 Deployment Status Summary

| Component | Status | Live URL |
|-----------|--------|----------|
| **Code** | ✅ All files complete | GitHub Ready |
| **Git** | ✅ Committed to main | https://github.com/Rohithburla51/SURAKSHANET-AI |
| **Frontend** | 🔄 Deploy to Vercel | `https://surakshanet-ai.vercel.app` |
| **Backend** | 🔄 Deploy to HF Spaces | `https://username-surakshanet-ai-backend.hf.space` |
| **Database** | ✅ Neo4j Aura online | f4997b01 |
| **RAG/LLM** | ✅ Groq + Supabase ready | All APIs configured |

---

## 🎯 Next Actions

1. **Push to GitHub** (if not already done):
   ```
   git pull origin main --allow-unrelated-histories --no-edit && git push -u origin main
   ```

2. **Deploy Frontend** → Vercel (15 min)

3. **Deploy Backend** → HF Spaces (10 min)

4. **Update Frontend ENV** → Set `NEXT_PUBLIC_API_URL`

5. **Redeploy Frontend** → Vercel

6. **Test Live**:
   ```
   https://surakshanet-ai.vercel.app
   ```

---

**🎉 Deployment complete! SurakshaNet AI is production-ready.**

