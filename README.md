# 🛡️ SurakshaNet AI — Indian Financial Crime Prevention Platform

> **A Unified Multi-Agent Intelligence Platform** for Real-Time Scam Detection, Counterfeit Currency Identification, and Police Fraud Investigation.

---

## 🎯 The Problem

India's digital financial revolution has democratized access but simultaneously scaled cybercrime:

- **Digital Arrest Scams**: Fraudsters impersonate CBI/ED officials, coercing victims into transferring life savings via video calls.
- **KYC/Banking Phishing**: Mass SMS campaigns exploit users with false account-blocking threats.
- **UPI Collect Fraud**: Scammers trick users into entering UPI PINs under false pretenses.
- **Counterfeit Currency Injection**: High-grade fake notes circulate through branches, bypassing manual teller checks.

### The Systemic Failure
Intelligence is **completely siloed**:
- Citizens lack instant verification tools.
- Bank tellers rely on slow manual checks.
- Law enforcement operates on fragmented databases where telecom, banking, and cyber complaints never sync.

---

## ✨ The Solution

**SurakshaNet AI** establishes a unified, three-portal ecosystem powered by state-of-the-art agents:

```
                  ┌────────────────────────────────┐
                  │      SURAKSHANET AI CORE       │
                  │  (FastAPI + Groq + Neo4j)      │
                  └───┬────────────┬────────┬───────┘
                      │            │        │
          ┌───────────┘            │        └────────────┐
          ▼                        ▼                     ▼
    ┌──────────────┐         ┌──────────────┐    ┌────────────────┐
    │   CITIZEN    │         │   BANK       │    │    POLICE      │
    │   PORTAL     │         │   PORTAL     │    │    PORTAL      │
    ├──────────────┤         ├──────────────┤    ├────────────────┤
    │• Text/Audio  │         │• OpenCV      │    │• Neo4j Graph   │
    │  Scam Check  │         │  Forensics   │    │• Multi-Hop     │
    │• Risk Gauge  │         │• LLaVA Vision│    │  Tracing       │
    │• Bilingual   │         │• Verdict     │    │• NL->Cypher    │
    │  Support     │         │  Banner      │    │  Translation   │
    └──────────────┘         └──────────────┘    └────────────────┘
```

### Portal 1: Citizen Safety (`/citizen`)
Users paste suspicious texts or upload call recordings. The system:
- Runs RAG-powered analysis against known Indian scam tactics.
- Outputs a **0–100 Risk Gauge** with color-coded verdict.
- Provides plain-English/Hindi explanations and instant action links.

### Portal 2: Bank Teller (`/bank`)
Tellers drop note images. The system:
- Executes OpenCV forensic checks (watermarks, microprint, intaglio sharpness).
- Combines with Groq LLaVA vision inference.
- Returns **GENUINE** | **SUSPECT** | **COUNTERFEIT** verdict with forensic breakdown.

### Portal 3: Police Intelligence (`/police`)
Investigators query the graph. The system:
- Maps mule accounts, phone numbers, UPI IDs, ringleaders, and victims visually.
- Supports Natural Language queries (e.g., "Find all mules connected to Operator Alpha").
- Shows real-time relationship traversals with summary insights.

---

## 🚀 Tech Stack

| Layer | Technology | Why This Choice |
| :--- | :--- | :--- |
| **Frontend** | Next.js 14 (Vercel) | Zero cold starts, edge caching, free forever tier |
| **Backend** | FastAPI (Hugging Face Spaces) | Never sleeps, ideal for hackathons, serverless Python |
| **Relational DB** | Supabase PostgreSQL | Instant UI, pgvector for RAG, zero laptop RAM |
| **Vector Search** | pgvector (Supabase) | Persistent embeddings, SQL similarity queries |
| **Graph DB** | Neo4j Aura (Free Tier) | 200MB free, hosted, zero setup |
| **LLM/Vision** | Groq API | Sub-second inference, daily limit of ~14k requests |
| **Caching** | Upstash Redis | Serverless, 10k free requests/day |
| **Styling** | Tailwind CSS (Pure) | Zero dependencies, compact bundle, dark-mode native |

---

## 🛠️ Setup & Installation

### Prerequisites
- **Node.js** >= 18 (Frontend)
- **Python** >= 3.10 (Backend)
- **Git** for version control

### Step 1: Clone Repository
```bash
git clone https://github.com/YourOrg/surakshanet-ai.git
cd surakshanet-ai
```

### Step 2: Environment Setup
Copy the example env file and fill in your credentials:
```bash
cp .env.example .env
```

Edit `.env` with:
- `GROQ_API_KEY` from [console.groq.com](https://console.groq.com)
- `DATABASE_URL` from Supabase dashboard
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` from Neo4j Aura
- `UPSTASH_REDIS_URL` from Upstash console
- `HUGGINGFACE_API_KEY` from Hugging Face

### Step 3: Backend Setup
```bash
# Create virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI server
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs on `http://localhost:8000`

### Step 4: Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend runs on `http://localhost:3000`

Navigate to:
- `/citizen` — Scam Detection Portal
- `/bank` — Counterfeit Verification Portal
- `/police` — Law Enforcement Intelligence Dashboard

---

## 📁 Project Structure

```
surakshanet-ai/
├── backend/
│   ├── agents/
│   │   ├── scam_agent.py          # Groq 120B + pgvector RAG
│   │   ├── counterfeit_agent.py   # OpenCV + Groq LLaVA 90B
│   │   └── network_agent.py       # NL-to-Cypher + Neo4j traversal
│   ├── api/
│   │   ├── routes/
│   │   │   ├── scam.py            # POST /api/scam/{text,audio}
│   │   │   ├── counterfeit.py     # POST /api/counterfeit/scan
│   │   │   └── network.py         # POST /api/network/query
│   │   └── __init__.py
│   ├── services/
│   │   ├── database.py            # Supabase asyncpg + pgvector
│   │   └── neo4j_graph.py         # Neo4j driver + constraints
│   ├── core/
│   │   └── demo_responses.py      # Fallback fixtures
│   └── main.py                    # FastAPI entrypoint
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx         # Root layout + CDN injection
│   │   │   ├── globals.css        # Tailwind + vis-network styles
│   │   │   ├── citizen/
│   │   │   │   └── page.tsx       # Scam analysis portal
│   │   │   ├── bank/
│   │   │   │   └── page.tsx       # Counterfeit detection portal
│   │   │   └── police/
│   │   │       └── page.tsx       # Graph intelligence dashboard
│   │   ├── components/
│   │   │   ├── RiskScore.tsx      # Animated risk gauge
│   │   │   ├── CounterfeitReport.tsx # Forensic verdict banner
│   │   │   └── NetworkGraph.tsx   # vis-network integration
│   │   └── lib/
│   │       └── api.ts            # Typed HTTP client
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── next.config.js
├── .env.example
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 🔑 Key Features

### Citizen Portal (`/citizen`)
- **Text Input**: Paste suspicious SMS/WhatsApp messages.
- **Audio Upload**: Record live phone calls and upload for analysis.
- **Risk Gauge**: Animated SVG showing 0–100 risk score with color thresholds.
- **Bilingual Output**: English + Hindi explanations.
- **Action Buttons**: Direct links to 1930 Cyber Crime Helpline, NCRB reporting.
- **Demo Mode**: Pre-filled scam text for instant testing.

### Bank Portal (`/bank`)
- **Image Dropzone**: Drag-and-drop or click to upload currency note photos.
- **Denomination Selector**: Choose ₹100, ₹200, ₹500, ₹2000.
- **Forensic Breakdown**: OpenCV metrics displayed as progress bars (watermark opacity, intaglio sharpness, etc.).
- **Verdict Banner**: High-contrast GENUINE/SUSPECT/COUNTERFEIT banner.
- **Features List**: Red chips for failed security checks.
- **Recommended Actions**: Escalation workflow for suspicious notes.

### Police Portal (`/police`)
- **Natural Language Query**: "Find all mules connected to Operator Alpha"
- **Structured Filters**: Phone number and bank account trace modes.
- **Network Visualization**: vis-network graph with color-coded nodes:
  - **Red**: FraudActors (ringleaders)
  - **Purple**: Syndicates
  - **Slate**: Phone Numbers
  - **Amber**: Bank Accounts
- **Query Summary**: Plain-English explanation of the graph.
- **Cypher Display**: Raw Neo4j query for transparency.

---

## 🧠 Agent Architecture

### Scam Analysis Agent
**File**: `backend/agents/scam_agent.py`

1. **Input**: User text or transcribed audio.
2. **RAG**: Query Supabase pgvector for top 3 similar historical scams.
3. **Inference**: Send to Groq `openai/gpt-oss-120b` with system prompt.
4. **Output**: `ScamAnalysisResult` (risk_score, category, tactics, red_flags, explanation).
5. **Fallback**: If Groq times out, return demo fixture from `demo_responses.py`.

### Counterfeit Detection Agent
**File**: `backend/agents/counterfeit_agent.py`

1. **Input**: Uploaded currency note image (bytes).
2. **OpenCV**:
   - CLAHE contrast enhancement.
   - FFT watermark opacity check.
   - Laplacian variance (intaglio sharpness).
   - Sobel edge density (print quality).
3. **Vision**: Encode image as base64, send to Groq `llama-3.2-90b-vision-preview`.
4. **Output**: `CounterfeitResult` (GENUINE/SUSPECT/COUNTERFEIT, forensic scores, features_passed/failed).
5. **Fallback**: Return conservative SUSPECT fixture if vision API fails.

### Network Intelligence Agent
**File**: `backend/agents/network_agent.py`

1. **Input**: Natural language query (e.g., "Find mules linked to Operator Alpha").
2. **Translation**: Send to Groq `llama-3.3-70b-versatile` with Neo4j schema context.
3. **Safety Check**: Enforce read-only Cypher (no MERGE/CREATE/DELETE).
4. **Execution**: If safe, run query against Neo4j Aura.
5. **Summarization**: Pass raw results back to Groq for plain-English summary.
6. **Output**: `NetworkQueryResult` (cypher_query, nodes, edges, summary).
7. **Fallback**: Return demo actor-lookup fixture on errors.

---

## 📊 API Endpoints

### Scam Analysis
```bash
# Text analysis
POST /api/scam/text
Content-Type: application/json
{
  "text": "CBI officer claims your Aadhaar is linked to narcotics smuggling..."
}
→ ScamAnalysisResult

# Audio analysis (with automatic transcription)
POST /api/scam/audio
Content-Type: multipart/form-data
{
  "audio": <binary audio file>
}
→ ScamAnalysisResult

# Unified endpoint (auto-detect)
POST /api/scam/analyze
```

### Counterfeit Detection
```bash
# Scan a currency note
POST /api/counterfeit/scan
Content-Type: multipart/form-data
{
  "image": <binary image>,
  "denomination": 500
}
→ CounterfeitResult

# Get list of denominations
GET /api/counterfeit/denominations
→ ["100", "200", "500", "2000"]
```

### Network Intelligence
```bash
# Natural language query
POST /api/network/query
Content-Type: application/json
{
  "question": "Find all mules connected to Operator Alpha"
}
→ NetworkQueryResult

# Raw Cypher query (for advanced users)
POST /api/network/cypher
Content-Type: application/json
{
  "query": "MATCH (a:FraudActor)-[r]->(b) RETURN a, r, b LIMIT 50"
}
→ NetworkQueryResult
```

### Health & Ready
```bash
# Liveness check
GET /health
→ 200 OK

# Readiness check
GET /ready
→ 200 OK (all services connected)
```

---

## 🚢 Deployment

### Deploy Frontend (Vercel)
1. Push code to GitHub.
2. Connect repo to Vercel via dashboard.
3. Set environment variables in Vercel settings.
4. Auto-deploys on every push to `main`.

```bash
# Manual deployment (optional)
npm run build
vercel deploy --prod
```

### Deploy Backend (Hugging Face Spaces)
1. Create a new Space on Hugging Face (Docker template).
2. Copy `requirements.txt` and `backend/` to the Space.
3. Create a `Dockerfile`:

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
```

4. Push to the Space repo — auto-deploys.
5. Space URL becomes your `NEXT_PUBLIC_API_URL`.

---

## 🧪 Testing & Demo Mode

### Enable Demo Mode
Set `DEMO_MOCK_MODE=true` in `.env` to use pre-baked responses without external API calls:

```env
DEMO_MOCK_MODE=true
```

**Demo Fixtures**:
- **Scam**: Digital Arrest (97% risk), KYC Phishing (89% risk), UPI Fraud (82% risk), Safe (4% risk).
- **Counterfeit**: Genuine ₹500, Suspect ₹500, Counterfeit ₹500.
- **Network**: Actor lookup, Phone trace, Empty result, Unsafe query rejection.

### Quick Test Flow
1. Navigate to `/citizen` → Click "Try Demo" → See Digital Arrest analysis.
2. Navigate to `/bank` → Click "Load Demo Suspect Note" → See counterfeit forensics.
3. Navigate to `/police` → Select "NL Query" tab → See actor network graph.

---

## 🔐 Security & Compliance

### Input Validation
- All endpoints validate input via Pydantic models.
- File uploads capped at 15MB.
- Image format whitelist: JPEG, PNG, WebP.

### Query Safety
- Network agent enforces read-only Cypher (regex blocks MERGE/CREATE/DELETE).
- All API responses strip sensitive PII before returning to frontend.

### Environment Secrets
- API keys stored in `.env` (git-ignored).
- Never commit `.env` — use `.env.example` as template.
- Rotate keys regularly via provider dashboards.

---

## 📈 Performance Benchmarks

| Operation | Latency | Model |
| :--- | :--- | :--- |
| Scam text analysis | 0.8–1.5s | Groq 120B |
| Audio transcription + analysis | 2–3s | Groq Whisper + 120B |
| Counterfeit image analysis | 1–2s | OpenCV + Groq LLaVA |
| Network NL query (3-hop) | 1–2s | Groq 70B + Neo4j |
| Network visualization (8 nodes) | <50ms | vis-network |

---

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/your-feature`.
3. Commit changes: `git commit -am 'Add your feature'`.
4. Push to branch: `git push origin feature/your-feature`.
5. Open a Pull Request.

---

## 📄 License

This project is licensed under the **MIT License**. See `LICENSE` file for details.

---

## 📞 Support & Contact

- **Cyber Crime Report**: Call **1930** or visit [cybercrime.gov.in](https://cybercrime.gov.in)
- **RBI Counterfeit Cell**: [rbi.org.in/counterfeit](https://www.rbi.org.in)
- **NCRB Complaint**: [crime.gov.in](https://crime.gov.in)

---

## 🎓 Architecture & Technical Deep Dive

### Database Schema

**Supabase PostgreSQL** (Relational):
```sql
-- Scam corpus for RAG
CREATE TABLE known_scams (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category VARCHAR(50),
  raw_text TEXT,
  embedding VECTOR(384),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Case tracking
CREATE TABLE cases (
  id UUID PRIMARY KEY,
  case_id VARCHAR UNIQUE,
  status VARCHAR,
  created_at TIMESTAMP
);
```

**Neo4j Aura** (Graph):
```cypher
-- Nodes
CREATE CONSTRAINT actor_name IF NOT EXISTS FOR (a:FraudActor) REQUIRE a.name IS UNIQUE;
CREATE CONSTRAINT phone_number IF NOT EXISTS FOR (p:PhoneNumber) REQUIRE p.number IS UNIQUE;
CREATE CONSTRAINT bank_account IF NOT EXISTS FOR (b:BankAccount) REQUIRE b.account_id IS UNIQUE;

-- Relationships
MATCH (a:FraudActor), (p:PhoneNumber)
CREATE (a)-[:USES]->(p);
```

### Data Flow
1. **User Input** → Frontend validation (15MB cap, format check).
2. **API Request** → Backend receives multipart/JSON.
3. **Agent Processing** → Async tasks (RAG lookup, LLM inference, CV processing).
4. **Persistence** → Results stored in Supabase (audit trail).
5. **Graph Updates** → Network intelligence persisted to Neo4j.
6. **Frontend Render** → Real-time WebSocket updates (future phase).

---

## 🎯 Roadmap

### Phase 6 ✅ (Current)
- [x] UI Polish & cross-browser testing
- [x] Environment setup (package.json, requirements.txt)
- [x] Production README
- [ ] GitHub Actions CI/CD pipeline

### Phase 7 (Future)
- [ ] WebSocket real-time alerts
- [ ] CartoDB heatmaps for Police portal
- [ ] Multi-language support (8+ Indian languages)
- [ ] Mobile app (React Native)
- [ ] Blockchain audit trail

---

## ⭐ Acknowledgments

Built with ❤️ for Indian financial crime prevention. Special thanks to:
- **Groq** for sub-second LLM inference
- **Supabase** for serverless PostgreSQL + pgvector
- **Neo4j** for graph database innovation
- **Next.js** for zero-config frontend framework

---

**Made with 🛡️ in India. Deployed globally. Protecting every citizen.**

---

*Last Updated: June 27, 2026 | SurakshaNet AI v1.0*
