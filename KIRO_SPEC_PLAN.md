# 🎯 KIRO_SPEC_PLAN.md
## Technical Specification & Task-Model Routing Blueprint

This master engineering file dictates the multi-phase execution strategy for **SurakshaNet AI**. Drop this file directly into your repository root directory. Kiro scans root specification markdown files to orchestrate its file-generation agents seamlessly.

---

## 🧭 Kiro Pro Credit Optimization Engine

To conserve your 1,000 monthly credits while maximizing code precision, Kiro must auto-route internal models according to task weight complexity. 

| Task Complexity | Assigned Kiro Model | Multiplier Cost | Scope of Work |
| :--- | :--- | :--- | :--- |
| **HEAVY** | `Claude Sonnet 4.6` | **1.3x** | DB Schema layout, pgvector logic, raw OpenCV matrix math, NL-to-Cypher translations. |
| **MEDIUM** | `DeepSeek 3.2` | **0.25x** | FastAPI router endpoints, state tickers, parsing API responses, Next.js contexts. |
| **LIGHT** | `Qwen3 Coder Next` | **0.05x** | Basic styling layouts, boilerplate wrappers, environment variables, documentation. |

---

## 🛠️ Phase-by-Phase Build Matrix

### PHASE 1: Relational & Graph Storage Layer
*   **Target Model Config:** `Claude Sonnet 4.6 (1.3x)`
*   **Tasks:**
    1. Provision async connections to Supabase PostgreSQL using `asyncpg`.
    2. Register the SQL vector extension schema for persistent RAG injection.
    3. Initialize connection pools for Neo4j Aura Graph DB using the native TLS `neo4j+s://` driver.
    4. Generate explicit node constraints for phone records, bank entries, and actors.

### PHASE 2: Core Multi-Agent Backends (`backend/agents/`)
*   **Target Model Config:** `Claude Sonnet 4.6 (1.3x)`
*   **Tasks:**
    1. **`scam_agent.py`:** Hook up Groq's high-tier inference API (`openai/gpt-oss-120b`). Feed context arrays retrieved natively via SQL similarity metrics (`<=>`). Enforce strict JSON output parsing.
    2. **`counterfeit_agent.py`:** Write forensic math sub-routines (Fast Fourier Transform for watermark opacity, Laplacian matrix variance for print sharpness). Bundle processed image buffers into base64 structures to evaluate on Groq’s high-precision 90B vision engine.
    3. **`network_agent.py`:** Compile exact instructional templates to securely translate human language logs into valid, execution-ready Neo4j Cypher scripts (`llama-3.3-70b-versatile`).

### PHASE 3: Rest API Core Routers (`backend/api/routes/`)
*   **Target Model Config:** `DeepSeek 3.2 (0.25x)`
*   **Tasks:**
    1. Establish the FastAPI application instance wrapped with global CORS configurations.
    2. Assemble individual structural routers for citizen analysis payloads, bank scanning requests, and tactical network queries.
    3. Implement explicit Pydantic request-response validation frameworks.
    4. Ensure all agent wrappers incorporate unified fail-safe `try/except` captures that fallback gracefully to mock demo data if external servers report rate limits or timing constraints.

### PHASE 4: Frontend Framework & Stakeholder Hub (`frontend/`)
*   **Target Model Config:** `DeepSeek 3.2 (0.25x)`
*   **Tasks:**
    1. Organize the Next.js 14 App Router directory structure matching custom dashboard viewports.
    2. Build baseline state controls to govern loading progressions, tabular filters, and multi-step uploads.
    3. Configure custom asynchronous fetch modules to communicate securely with the FastAPI backend endpoint server.

### PHASE 5: Advanced CDN Visualizations (`frontend/src/components/`)
*   **Target Model Config:** `Claude Sonnet 4.6 (1.3x)`
*   **Tasks:**
    1. Inject Leaflet.js map structures dynamically into layout wrappers using native browser runtime injections.
    2. Construct interactive network graph layouts inside canvas contexts using CDN versions of `vis-network`. Ensure nodes display contrasting color weight scales matching criminal rank data.
    3. Configure WebSocket streams to handle incoming server alerts seamlessly with reactive toast notifications.

### PHASE 6: UI Polish & Documentation
*   **Target Model Config:** `Qwen3 Coder Next (0.05x)`
*   **Tasks:**
    1. Polish cross-browser Tailwind element positioning, custom font variables, and micro-interactions.
    2. Set up template environment keys.
    3. Author the absolute master production `README.md`.

---

## 📝 Rules of Engagement for Kiro Engine
1. Do not use local dependencies or heavy Python database environments inside containers. Everything shifts to serverless endpoints or CDN links.
2. Read and strictly abide by the assigned task-to-model configuration weights documented in this blueprint file.
3. Every external inference call requires safety wrappers and predictable fallback loops.
