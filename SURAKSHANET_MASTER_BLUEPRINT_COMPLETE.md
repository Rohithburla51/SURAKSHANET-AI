# 🛡️ SURAKSHANET AI — MASTER PROJECT BLUEPRINT
## The Definitive Guide: Problem Statement, Solution Architecture, Zero-Cost Tech Stack, Step-by-Step Build Guide, and Perpetual Deployment Plan.

---

## SECTION 1: THE PROBLEM STATEMENT

India is undergoing the fastest digital financial revolution in human history. With over 10 billion monthly UPI transactions and rapid digital onboarding, financial access has democratized. However, **cybercrime has scaled alongside it at an alarming rate.** 

Indian citizens, financial institutions, and law enforcement face four critical threat vectors:

1. **The Digital Arrest Epidemic:** Fraudsters impersonate high-ranking officials from the CBI, ED, Customs, or Police via video/audio calls, falsely claiming the victim's Aadhaar is linked to money laundering or drug trafficking. Victims are psychologically held hostage and coerced into transferring life savings to "secret verification accounts."
2. **KYC & Banking Phishing Waves:** Mass SMS/WhatsApp campaigns claiming a user's Bank, Jio, or Airtel account will be blocked within 24 hours unless an urgent APK is downloaded or an OTP is shared.
3. **UPI "Collect Request" Deception:** Scammers trick non-technical users into entering their UPI PIN under the false premise of *receiving* a lottery prize, refund, or second-hand marketplace payment.
4. **Physical Counterfeit Injection:** Bad actors inject high-grade counterfeit ₹100, ₹200, ₹500, and ₹2000 currency notes into local circulation, exploiting bank branch tellers who rely strictly on slow, manual sensory verification.

### The Core Systemic Failure
**Intelligence is completely siloed.** Citizens do not have an instant, vernacular tool to verify suspicious interactions. Bank tellers lack automated structural computer vision at the counter. Law enforcement sits on fragmented databases where telecom call logs, bank mule accounts, and cyber police complaints never talk to each other in real-time.

---

## SECTION 2: THE SOLUTION ARCHITECTURE

**SurakshaNet AI** solves this systemic failure by establishing a unified, multi-agent intelligence ecosystem split into three dedicated operational portals:

```
                  ┌────────────────────────────────────────┐
                  │          SURAKSHANET AI CORE           │
                  │   (FastAPI + Groq LLM/Vision/Whisper)  │
                  └───────┬───────────────┬────────┬───────┘
                          │               │        │
            ┌─────────────┘               │        └─────────────┐
            ▼                             ▼                      ▼
  ┌───────────────────┐        ┌───────────────────┐  ┌────────────────────┐
  │  CITIZEN PORTAL   │        │ BANK TELLER PORTAL│  │   POLICE PORTAL    │
  │     (/citizen)    │        │      (/bank)      │  │     (/police)      │
  ├───────────────────┤        ├───────────────────┤  ├────────────────────┤
  │• Text/Audio Scan  │        │• OpenCV Structural│  │• Neo4j Graph DB    │
  │• pgvector RAG     │        │  Feature Checking │  │• Multi-Hop Tracing │
  │• "Suraksha Sathi" │        │• LLaVA Multimodal │  │• NL -> Cypher AI   │
  │  Bilingual Copilot│        │  Anomaly Verdict  │  │• CartoDB Heatmaps  │
  └───────────────────┘        └───────────────────┘  └────────────────────┘
```

1. **The Citizen Safety Portal (`/citizen`):** Allows users to paste suspicious text messages or upload live phone call audio recordings. The system runs Retrieval-Augmented Generation (RAG) against known Indian scam tactics and provides a plain-English/Hindi explanation, an animated 0–100 Risk Gauge, and instant action links (Call 1930 Helpline / File NCRB Report).
2. **The Bank Teller Portal (`/bank`):** Allows tellers to drop a note image. The system executes structural OpenCV checks (watermarks, micro-lettering, intaglio print sharpness) combined with Groq LLaVA vision inference to output an instant **GENUINE**, **SUSPECT**, or **COUNTERFEIT** verdict.
3. **The Police Intelligence Dashboard (`/police`):** A graph-powered command center. Investigators enter a phone number or UPI ID to instantly generate a visual node network mapping connected mule accounts, ringleaders, and victims across state lines. Includes a Natural Language-to-Cypher AI query box.

---

## SECTION 3: THE OPTIMIZED TECH STACK (GATEKEEPER CHOICE)

To guarantee this project deploys in seconds for hackathon judging **and stays live on your resume forever without costing ₹1**, we reject expiring cloud trials and heavy RAM bottlenecks. 

| Infrastructure Layer | Standard Hackathon Approach | **SurakshaNet Optimized Choice** | **The Strategic Gatekeeper Justification** |
| :--- | :--- | :--- | :--- |
| **Frontend Platform** | Next.js on Vercel | **Next.js 14 on Vercel (Hobby Tier)** | 100% free forever. Edge-cached, zero cold starts, seamless GitHub auto-CI/CD. |
| **Backend Host** | Render Free Tier | **Hugging Face Spaces (Docker Python)** | *Crucial Optimization:* Render free backends go to sleep after 15 mins of idle time, causing 50s delays for recruiters. Hugging Face Spaces (using a Docker FastAPI blueprint) **never sleeps**. |
| **Relational DB** | Local Docker Postgres | **Supabase Cloud PostgreSQL** | Instant browser UI, zero laptop RAM usage, robust relational data integrity. |
| **Vector Search** | Local FAISS Index in RAM | **Supabase `pgvector` Extension** | *Crucial Optimization:* Replaces volatile in-memory JSON embedding loads with persistent, highly optimized SQL vector similarity queries. |
| **Graph Database** | Local Neo4j Container | **Neo4j Aura Cloud (Free Tier)** | Hosted cloud graph database giving 200MB free forever. Zero setup. |
| **LLM & Vision Engine**| Local Ollama / OpenAI Paid | **Groq Cloud API** | Daily resetting limit of ~14,400 requests/day. Sub-second inference for Llama 3.1 8B, Whisper Large v3, and LLaVA Vision. |
| **Caching Layer** | Local Redis | **Upstash Redis Cloud** | Serverless HTTP Redis giving 10,000 free requests/day. |

---

## SECTION 4: STEP-BY-STEP IMPLEMENTATION GUIDE

### Phase 1: Cloud Provisioning & Environment Setup (Hours 0–3)
1. **Groq Console:** Generate an API Key (`gsk_...`).
2. **Supabase:** Create project `surakshanet-db`. Run this SQL in the SQL Editor to enable vectors:
   ```sql
   create extension if not exists vector;
   create table known_scams (
     id uuid primary key default gen_random_uuid(),
     category varchar,
     raw_text text,
     embedding vector(384)
   );
   ```
3. **Neo4j Aura:** Launch a free instance. Save the `neo4j+s://...` URI and generated password.
4. **Upstash:** Create a Redis database and copy the `UPSTASH_REDIS_URL`.

### Phase 2: FastAPI Backend Scaffold (Hours 3–15)
Create `backend/` directory containing:

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import scam, counterfeit, network, geo, copilot

app = FastAPI(title="SurakshaNet AI API", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(scam.router, prefix="/api/scam")
app.include_router(counterfeit.router, prefix="/api/counterfeit")
app.include_router(network.router, prefix="/api/network")
app.include_router(geo.router, prefix="/api/geo")
app.include_router(copilot.router, prefix="/api/copilot")

@app.get("/health")
def health():
    return {"status": "online", "stack": "HuggingFace+Supabase+Groq"}
```

**Core Service Implementations:**
* `services/groq_service.py`: Initialize `AsyncGroq(api_key=...)`. Wrap `.chat.completions.create` and `.audio.transcriptions.create`.
* `services/vector_service.py`: Connect to Supabase via `psycopg2`. Execute `SELECT category, raw_text FROM known_scams ORDER BY embedding <=> $1 LIMIT 3`.
* `agents/counterfeit_agent.py`: Implement OpenCV CLAHE enhancement + Sobel edge detection for bleed lines, piped alongside base64 encoded strings to Groq's `llava-v1.5-7b` endpoint.

### Phase 3: Next.js Frontend Scaffold (Hours 15–30)
Create `frontend/` using Next.js App Router:
* Inject Leaflet and vis-network into `src/app/layout.tsx` head directly via CDN:
  ```html
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/standalone/umd/vis-network.min.js"></script>
  ```
* **Citizen UI (`/citizen`):** Textarea + File dropzone. On submit, POST to `/api/scam/analyze`. Render SVG Circular Progress Gauge based on returned `risk_score`.
* **Police UI (`/police`):** Search input. On submit, pass returned nodes/edges JSON directly to `new window.vis.Network(container, data, options)`.

### Phase 4: Data Seeding (Hours 30–35)
Run a local script `seed_cloud.py`:
1. Push 40 distinct Indian scam SMS strings into Supabase `known_scams` table (generate embeddings via free HuggingFace `all-MiniLM-L6-v2` route).
2. Execute Cypher queries on Neo4j Aura to create syndicate *"Operation Jharkhand Ring"*:
   ```cypher
   CREATE (r:FraudActor {name:'Operator Alpha', role:'RINGLEADER', state:'Jharkhand'})
   CREATE (p1:PhoneNumber {number:'+919876543210'})
   CREATE (b1:BankAccount {bank:'SBI', acc:'XXXX1234'})
   CREATE (r)-[:USES]->(p1)
   CREATE (r)-[:CONTROLS]->(b1)
   ```

---

## SECTION 5: PLAN OF ACTION (EXECUTION PROTOCOLS)

### Protocol A: The 48-Hour Hackathon Sprint
* **Hour 0–4:** Setup GitHub Monorepo + Cloud Accounts. Verify API keys.
* **Hour 4–18:** Build Backend routes. Implement `DEMO_MOCK_MODE=True` switch in `config.py` that intercepts failing external calls and instantly returns pre-formatted JSON responses. *Never let network latency kill a live live demo.*
* **Hour 18–34:** Build Frontend pages (`/`, `/citizen`, `/bank`, `/police`). 
* **Hour 34–40:** Hook up deployment pipelines. Vercel for Frontend, Render/HuggingFace for Backend.
* **Hour 40–48:** End-to-end rehearsal using the 3-Minute Presentation Script.

### Protocol B: Perpetual Resume Hardening (Post-Hackathon Day 3)
To ensure this software remains stable for recruiters 6 months from now:

1. **Eliminate Database Sleep:** Supabase pauses clusters after 7 days of inactivity. Create `.github/workflows/keep_alive.yml`:
   ```yaml
   name: Supabase Keep-Alive
   on:
     schedule:
       - cron: '0 0 */3 * *' # Runs every 3 days
   jobs:
     ping:
       runs-on: ubuntu-latest
       steps:
         - run: curl -X GET https://your-backend-url/health
   ```
2. **Eliminate Backend Sleep:** If using Render instead of HuggingFace Spaces, register your backend URL on **Cron-job.org** and schedule an HTTP GET request every **14 minutes**.
3. **Portfolio Polish:** Claim your free 1-year `.tech` or `.me` domain from the **GitHub Student Developer Pack**. Map it to Vercel inside project settings.

---

## SECTION 6: COMPLETE DIRECTORY STRUCTURE

```text
surakshanet-ai/
├── .github/
│   └── workflows/
│       └── keep_alive.yml        ← Automated 3-day cron to prevent cloud sleep
├── backend/
│   ├── Dockerfile                ← Configures HuggingFace Spaces Python runtime
│   ├── main.py                   ← FastAPI routing engine
│   ├── requirements.txt
│   ├── .env.example
│   ├── api/
│   │   └── routes/
│   │       ├── scam.py           ← Citizen scam analysis route
│   │       ├── counterfeit.py    ← Bank note vision route
│   │       ├── network.py        ← Police syndicate graph route
│   │       ├── geo.py            ← Heatmap coordinates route
│   │       └── copilot.py        ← Chatbot companion route
│   ├── agents/
│   │   ├── scam_agent.py         ← Groq LLM + pgvector logic
│   │   ├── counterfeit_agent.py   ← OpenCV structure + LLaVA vision logic
│   │   ├── network_agent.py      ← NL to Cypher translation logic
│   │   └── copilot_agent.py      ← Safety assistant logic
│   └── services/
│       ├── groq_service.py       ← Groq Cloud API wrapper
│       ├── supabase_service.py   ← Postgres & pgvector wrapper
│       └── neo4j_service.py      ← Aura Graph DB wrapper
├── frontend/
│   ├── package.json
│   ├── vercel.json               ← Vercel deployment config
│   └── src/
│       ├── app/
│       │   ├── layout.tsx        ← Global CDN script injection
│       │   ├── page.tsx          ← National Command Landing Page
│       │   ├── citizen/page.tsx  ← Citizen Safety Portal UI
│       │   ├── bank/page.tsx     ← Bank Teller Scanner UI
│       │   └── police/page.tsx   ← Police Graph & Query UI
│       └── components/
│           ├── RiskScore.tsx     ← Animated SVG circular gauge
│           ├── FraudGraph.tsx    ← vis-network CDN wrapper
│           ├── CrimeHeatmap.tsx  ← Leaflet CDN wrapper
│           └── CopilotChat.tsx   ← Chat companion UI
└── README.md
```

---
*Blueprint Archival Date: June 2026. Designed for perpetual zero-cost uptime.*
