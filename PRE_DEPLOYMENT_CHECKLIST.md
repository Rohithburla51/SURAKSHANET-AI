# ✅ SurakshaNet AI — Pre-Deployment Checklist

**Status**: Phase 6 Complete — Ready for Production  
**Date**: June 27, 2026  
**Total Files**: 36 production-ready files  

Use this checklist before deploying to production.

---

## 📋 Phase Verification Checklist

### Phase 1-2: Backend Agents ✅
- [x] `backend/agents/scam_agent.py` — Groq 120B + pgvector RAG
- [x] `backend/agents/counterfeit_agent.py` — OpenCV + Groq LLaVA 90B
- [x] `backend/agents/network_agent.py` — NL-to-Cypher + Neo4j
- [x] `backend/core/demo_responses.py` — All 3 agents have demo fixtures
- [x] All agents implement fallback to `DEMO_MOCK_MODE`

### Phase 3: REST API Routers ✅
- [x] `backend/main.py` — FastAPI app + CORS + health endpoints
- [x] `backend/api/routes/scam.py` — POST /api/scam/{text,audio,unified}
- [x] `backend/api/routes/counterfeit.py` — POST /api/counterfeit/scan
- [x] `backend/api/routes/network.py` — POST /api/network/{query,cypher}
- [x] `backend/services/database.py` — Supabase asyncpg + pgvector
- [x] `backend/services/neo4j_graph.py` — Neo4j TLS driver + constraints

### Phase 4: Citizen Portal ✅
- [x] `frontend/src/app/citizen/page.tsx` — Text/audio input + demo button
- [x] `frontend/src/components/RiskScore.tsx` — Animated SVG gauge 0-100
- [x] Bilingual output (English/Hindi) ✅
- [x] Try Demo button pre-fills scam message ✅

### Phase 4: Bank Portal ✅
- [x] `frontend/src/app/bank/page.tsx` — Dropzone + denomination select
- [x] `frontend/src/components/CounterfeitReport.tsx` — Verdict banner + forensics
- [x] 15MB file size validation ✅
- [x] Image format whitelist (JPEG, PNG, WebP) ✅

### Phase 5: Police Portal ✅
- [x] `frontend/src/app/police/page.tsx` — Sidebar + graph canvas
- [x] `frontend/src/components/NetworkGraph.tsx` — vis-network integration
- [x] NL query, phone trace, account trace modes ✅
- [x] Color-coded nodes (Red/Purple/Slate/Amber) ✅
- [x] Cypher query display ✅

### Phase 6: Polish & Documentation ✅
- [x] `requirements.txt` — All Python deps (pinned versions)
- [x] `frontend/package.json` — NPM scripts & dependencies
- [x] `frontend/tsconfig.json` — TypeScript strict mode
- [x] `frontend/tailwind.config.js` — Theme customization
- [x] `frontend/postcss.config.js` — CSS processing
- [x] `frontend/next.config.js` — Build optimization
- [x] `frontend/src/app/layout.tsx` — vis-network CDN injection
- [x] `frontend/src/app/globals.css` — Global styles + utilities
- [x] `.env.example` — Credential template (7 services)
- [x] `.gitignore` — Comprehensive patterns
- [x] `README.md` — 3,500+ lines master documentation
- [x] `DEPLOYMENT.md` — Production deployment guide
- [x] `CONTRIBUTING.md` — Development guidelines
- [x] `QUICKSTART.md` — 5-minute setup guide
- [x] `Dockerfile` — Backend Docker image for HF Spaces
- [x] `docker-compose.yml` — Local dev orchestration
- [x] `.github/workflows/deploy.yml` — CI/CD pipeline

---

## 🔑 Environment Setup

### Before Production Deployment

**Credentials Required** (7 services):

- [ ] **Groq API**: `GROQ_API_KEY=gsk_...`
  - Get from: [console.groq.com](https://console.groq.com)
  - Quota: ~14,400 requests/day

- [ ] **Supabase PostgreSQL**: `DATABASE_URL=postgresql://...`
  - Get from: [supabase.com](https://supabase.com)
  - Must enable `pgvector` extension
  - Run SQL schema setup

- [ ] **Neo4j Aura**: `NEO4J_URI=neo4j+s://...`, `NEO4J_USER`, `NEO4J_PASSWORD`
  - Get from: [console.neo4j.io](https://console.neo4j.io)
  - Run Cypher constraints setup

- [ ] **Upstash Redis**: `UPSTASH_REDIS_URL=rediss://...`
  - Get from: [console.upstash.com](https://console.upstash.com)
  - Quota: 10,000 requests/day

- [ ] **Hugging Face**: `HUGGINGFACE_API_KEY=hf_...`
  - Get from: [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
  - For embeddings model download

**Configuration Verification**:

```bash
# Test each credential
# Database
psql $DATABASE_URL -c "SELECT 1"

# Neo4j (requires neo4j-cli or browser)
curl $NEO4J_URI

# Groq
curl -H "Authorization: Bearer $GROQ_API_KEY" \
     https://api.groq.com/openai/v1/models

# Upstash
curl -X PING $UPSTASH_REDIS_URL
```

---

## 🚀 Frontend Deployment (Vercel)

### Pre-Deployment

- [ ] Code pushed to GitHub `main` branch
- [ ] All tests pass (`npm run lint`, `npm run type-check`)
- [ ] Build succeeds locally (`npm run build`)
- [ ] No hardcoded API URLs (use `NEXT_PUBLIC_API_URL`)

### Vercel Setup

- [ ] Vercel account created
- [ ] Repository connected to Vercel
- [ ] Environment variables set:
  ```
  NEXT_PUBLIC_API_URL=https://your-backend.hf.space
  ```
- [ ] Build command: `npm run build`
- [ ] Start command: `next start`
- [ ] Root directory: `frontend`

### Post-Deployment

- [ ] Frontend URL accessible: `https://your-app.vercel.app`
- [ ] Citizen portal loads: [http://localhost:3000/citizen](http://localhost:3000/citizen)
- [ ] Bank portal loads: [http://localhost:3000/bank](http://localhost:3000/bank)
- [ ] Police portal loads: [http://localhost:3000/police](http://localhost:3000/police)
- [ ] Demo buttons work (pre-fill data)
- [ ] No console errors
- [ ] Network graph renders (vis-network loaded)

---

## 🔙 Backend Deployment (Hugging Face Spaces)

### Pre-Deployment

- [ ] `requirements.txt` has pinned versions
- [ ] `Dockerfile` builds successfully: `docker build -t backend .`
- [ ] All secrets added to Space Settings
- [ ] Backend starts in demo mode without errors

### HF Spaces Setup

- [ ] Space created (Docker template)
- [ ] Repository cloned locally
- [ ] Backend files copied to Space
- [ ] Secrets configured:
  ```
  GROQ_API_KEY=...
  DATABASE_URL=...
  NEO4J_URI=...
  NEO4J_USER=...
  NEO4J_PASSWORD=...
  UPSTASH_REDIS_URL=...
  HUGGINGFACE_API_KEY=...
  DEMO_MOCK_MODE=false
  ```
- [ ] Code pushed to Space repo

### Post-Deployment

- [ ] Space URL visible: `https://username-surakshanet-ai-backend.hf.space`
- [ ] Health check passes:
  ```bash
  curl https://username-surakshanet-ai-backend.hf.space/health
  ```
- [ ] Liveness check passes:
  ```bash
  curl https://username-surakshanet-ai-backend.hf.space/ready
  ```
- [ ] No pod crashes in Space logs
- [ ] Endpoint `/docs` shows Swagger UI

---

## 🧪 Integration Testing

### Local Testing (Before Deployment)

```bash
# Terminal 1: Backend (demo mode)
cd backend
export DEMO_MOCK_MODE=true
uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Test endpoints
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/scam/text \
  -H "Content-Type: application/json" \
  -d '{"text":"Your Aadhaar is linked to crime..."}'
```

### Production Testing (Post-Deployment)

- [ ] Frontend loads from Vercel
- [ ] Backend responds from HF Spaces
- [ ] Scam portal: Text analysis works
- [ ] Scam portal: Audio upload works (Whisper transcription)
- [ ] Scam portal: Risk gauge renders & animates
- [ ] Bank portal: Image upload works
- [ ] Bank portal: Denomination selection works
- [ ] Bank portal: Forensic metrics display
- [ ] Police portal: NL query translates
- [ ] Police portal: Network graph renders
- [ ] All portals: Demo buttons populate data

### API Endpoint Verification

```bash
# Scam text analysis
POST /api/scam/text
→ Expected: ScamAnalysisResult (risk_score, category, explanation)

# Counterfeit scan
POST /api/counterfeit/scan
→ Expected: CounterfeitResult (verdict, forensic_metrics)

# Network NL query
POST /api/network/query
→ Expected: NetworkQueryResult (nodes, edges, cypher_query)

# Health check
GET /health
→ Expected: {"status": "healthy"}

# Readiness check
GET /ready
→ Expected: All services connected
```

---

## 📊 Performance Verification

### Frontend Metrics

- [ ] First Contentful Paint (FCP): < 2 seconds
- [ ] Largest Contentful Paint (LCP): < 3 seconds
- [ ] Cumulative Layout Shift (CLS): < 0.1
- [ ] Time to Interactive (TTI): < 4 seconds

**Check via**:
- Vercel Analytics dashboard
- Chrome DevTools Lighthouse
- Web Vitals in browser console

### Backend Metrics

- [ ] API response time: < 2s (scam), < 2s (counterfeit), < 2s (network)
- [ ] Database query time: < 500ms
- [ ] No timeout errors (Groq rate limit: 14k/day)
- [ ] Memory usage: < 500MB (HF Spaces limit: 16GB)
- [ ] Uptime: > 99% (monitor with health checks)

**Check via**:
- HF Spaces logs
- Groq console usage metrics
- Supabase query logs
- Neo4j performance metrics

---

## 🔐 Security Verification

### Secrets Management

- [ ] No API keys in `.env` (committed)
- [ ] `.gitignore` includes `.env` file
- [ ] All secrets in Vercel Environment Variables
- [ ] All secrets in HF Spaces Secrets
- [ ] No secrets in GitHub Secrets (only tokens)
- [ ] Credentials rotated quarterly

### Input Validation

- [ ] File upload size capped (15MB)
- [ ] Image format whitelist enforced
- [ ] Text input length limits enforced (1000 chars)
- [ ] SQL injection prevention (Pydantic validation)
- [ ] Cypher query safety checks (read-only enforcement)

### API Security

- [ ] CORS configured (allow frontend domain)
- [ ] Rate limiting on Groq calls
- [ ] No sensitive PII in API responses
- [ ] HTTPS enforced (Vercel + HF Spaces)
- [ ] Content Security Policy (CSP) headers set

---

## 📚 Documentation Verification

- [ ] README.md complete & up-to-date
- [ ] DEPLOYMENT.md covers both platforms
- [ ] CONTRIBUTING.md has clear guidelines
- [ ] QUICKSTART.md works (5-min test)
- [ ] API endpoints documented in `/docs`
- [ ] Code comments explain complex logic
- [ ] Function docstrings complete

---

## 🎯 Final Verification Steps

### Day Before Deployment

- [ ] All team members have access to credentials
- [ ] Backup & disaster recovery plan ready
- [ ] Monitoring alerts configured
- [ ] Support runbook prepared
- [ ] Rollback procedure documented

### Deployment Day

- [ ] Deploy frontend to Vercel first
- [ ] Verify frontend loads successfully
- [ ] Deploy backend to HF Spaces
- [ ] Wait 5 minutes for Space to build
- [ ] Verify backend health check
- [ ] Test all three portals end-to-end
- [ ] Monitor logs for errors (first 24 hours)

### Post-Deployment (First Week)

- [ ] Monitor Groq quota usage daily
- [ ] Check database storage growth
- [ ] Review error logs for anomalies
- [ ] Verify backups are running
- [ ] Collect user feedback
- [ ] Prepare hotfix for any issues

---

## 📞 Support & Rollback

### Rollback Procedure (If Issues Arise)

**Frontend**:
```bash
# Vercel Dashboard → Deployments → Select Previous Version → Promote
```

**Backend**:
```bash
# HF Space Settings → Versions → Restore Previous
```

### Escalation Contacts

- **Frontend Issues**: Vercel Support, GitHub Actions logs
- **Backend Issues**: HF Spaces logs, Groq console
- **Database Issues**: Supabase dashboard, Neo4j console
- **Team Contact**: [Your team email/Slack]

---

## ✅ Sign-Off Checklist

Before announcing production launch:

- [ ] CEO/Product Lead approval
- [ ] Tech lead verification
- [ ] Security audit completed
- [ ] Performance benchmarks met
- [ ] Documentation reviewed
- [ ] Team trained on deployment
- [ ] Monitoring configured
- [ ] Support plan in place

---

## 🎉 You're Ready!

Once all items are checked, SurakshaNet AI is production-ready.

**Expected Outcome**:
- ✅ Vercel frontend live
- ✅ HF Spaces backend live
- ✅ All three portals functional
- ✅ Demo mode optional (real APIs used)
- ✅ Monitoring & alerts active
- ✅ Support team ready

---

## Quick Links

- 📖 [README.md](./README.md)
- 🚀 [DEPLOYMENT.md](./DEPLOYMENT.md)
- ⚡ [QUICKSTART.md](./QUICKSTART.md)
- 📋 [PHASE_6_COMPLETION_REPORT.md](./PHASE_6_COMPLETION_REPORT.md)

---

*Checklist Last Updated: June 27, 2026*  
*SurakshaNet AI v1.0 — Production Ready*
