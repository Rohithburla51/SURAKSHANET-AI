# ⚡ SurakshaNet AI — Quick Start Guide

Get SurakshaNet AI running locally in **5 minutes** using demo mode (no external API keys needed).

---

## 🚀 30-Second Setup

### 1. Clone & Install
```bash
git clone https://github.com/YourOrg/surakshanet-ai.git
cd surakshanet-ai

# Backend
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### 2. Enable Demo Mode
Edit `.env`:
```bash
DEMO_MOCK_MODE=true
```

### 3. Run Locally
```bash
# Terminal 1: Backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

### 4. Open Browser
- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Try the Demos

### Citizen Portal (`/citizen`)
1. Navigate to [http://localhost:3000/citizen](http://localhost:3000/citizen)
2. Click **"Try Demo"** button
3. See a **Digital Arrest** scam analysis with 97% risk score

### Bank Portal (`/bank`)
1. Navigate to [http://localhost:3000/bank](http://localhost:3000/bank)
2. Click **"Load Demo Suspect Note"** button
3. See **SUSPECT** counterfeit verdict with forensic breakdown

### Police Portal (`/police`)
1. Navigate to [http://localhost:3000/police](http://localhost:3000/police)
2. Select **"NL Query"** tab
3. See **actor network graph** with connected mule accounts

---

## 📝 Test API Endpoints

### Scam Analysis (Demo)
```bash
curl -X POST http://localhost:8000/api/scam/text \
  -H "Content-Type: application/json" \
  -d '{"text":"Your Aadhaar is linked to a narcotics smuggling case..."}'
```

Response:
```json
{
  "risk_score": 97,
  "category": "digital_arrest",
  "verdict": "SCAM",
  "explanation": "This is a textbook Digital Arrest scam..."
}
```

### Counterfeit Detection (Demo)
```bash
# Upload a currency note image
curl -X POST http://localhost:8000/api/counterfeit/scan \
  -F "image=@/path/to/note.jpg" \
  -F "denomination=500"
```

Response:
```json
{
  "verdict": "SUSPECT",
  "final_score": 54,
  "features_failed": ["watermark_opacity", "intaglio_sharpness"]
}
```

### Network Query (Demo)
```bash
curl -X POST http://localhost:8000/api/network/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Find all mules connected to Operator Alpha"}'
```

Response:
```json
{
  "summary": "Operator Alpha is the central ringleader...",
  "nodes": [...],
  "edges": [...]
}
```

---

## 🔧 Common Tasks

### Check Backend Health
```bash
curl http://localhost:8000/health
# Returns: {"status": "healthy"}
```

### Enable Debug Logging
```bash
# Backend
LOGLEVEL=DEBUG uvicorn main:app --reload

# Frontend
npm run dev
# Check browser console for React DevTools output
```

### Run Linters
```bash
# Backend
flake8 backend/

# Frontend
npm run lint
```

### Run Type Checks
```bash
# Backend
mypy backend/

# Frontend
npm run type-check
```

---

## 🔌 Connect Real APIs (Advanced)

To use real Groq, Supabase, Neo4j, and Upstash services:

### 1. Get API Keys
- **Groq**: [console.groq.com](https://console.groq.com)
- **Supabase**: [supabase.com](https://supabase.com)
- **Neo4j**: [console.neo4j.io](https://console.neo4j.io)
- **Upstash**: [console.upstash.com](https://console.upstash.com)

### 2. Update `.env`
```bash
DEMO_MOCK_MODE=false
GROQ_API_KEY=gsk_your_key_here
DATABASE_URL=postgresql://...
NEO4J_URI=neo4j+s://...
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
UPSTASH_REDIS_URL=rediss://...
HUGGINGFACE_API_KEY=hf_...
```

### 3. Restart Backend
```bash
cd backend
uvicorn main:app --reload --port 8000
```

---

## 📚 Documentation

- **[README.md](./README.md)** — Full project overview & architecture
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** — Deploy to production (Vercel + HF Spaces)
- **[CONTRIBUTING.md](./CONTRIBUTING.md)** — Contribute code, report bugs
- **[API Docs (Swagger)](http://localhost:8000/docs)** — Interactive API documentation

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'fastapi'"
```bash
# Activate virtual environment
source venv/Scripts/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### "Cannot find module 'react'"
```bash
cd frontend
npm install
```

### "Port 8000 already in use"
```bash
# Use different port
uvicorn main:app --port 8001
```

### "Port 3000 already in use"
```bash
# Use different port
npm run dev -- -p 3001
```

### Demo mode not working
```bash
# Ensure DEMO_MOCK_MODE=true in .env
# Restart backend
```

### Visualizations not rendering
1. Check browser console for errors
2. Verify vis-network CDN is loaded (Network tab)
3. Try a different browser

---

## 💡 Next Steps

1. ✅ Explore the demo portals
2. 📖 Read [README.md](./README.md) for architecture details
3. 🔌 Connect real APIs for production use
4. 🚀 Deploy to Vercel + Hugging Face Spaces
5. 🤝 Contribute improvements via GitHub PRs

---

## 🆘 Need Help?

- **GitHub Issues**: Report bugs or ask questions
- **Discussions**: Join conversations with the community
- **Email**: maintainers@surakshanet.dev

---

**Happy coding! 🛡️**

*Updated: June 27, 2026*
