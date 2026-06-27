---
title: SurakshaNet AI Backend
emoji: 🛡️
colorFrom: blue
colorTo: green
sdk: docker
app_file: backend/main.py
pinned: false
---

LIVE PROJECT HOSTING LINK: https://surakshanet-ai.vercel.app/


# SurakshaNet AI — Multi-Agent Fraud Intelligence Platform

Production-ready backend for Indian financial crime prevention featuring three specialized AI agents.

## Features

- **Citizen Portal**: SMS/Email scam detection via RAG + Groq LLM
- **Bank Portal**: Currency note verification via OpenCV + LLaVA vision model
- **Police Dashboard**: Fraud network analysis via Neo4j graph queries

## Tech Stack

- **Backend**: FastAPI, Python 3.10
- **Databases**: Neo4j Aura, Supabase PostgreSQL
- **AI/ML**: Groq (Mixtral, LLaVA), OpenCV
- **Container**: Docker (HF Spaces)



## Endpoints

- `GET /health` - Health check
- `POST /api/scam/analyze` - Analyze scam messages
- `POST /api/counterfeit/verify` - Verify currency notes
- `POST /api/network/query` - Query fraud network

## Environment Variables

Required secrets (set in HF Space Settings):
- `GROQ_API_KEY`
- `DATABASE_URL`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `HUGGINGFACE_API_KEY`
- `DEMO_MOCK_MODE`

## Repository

https://github.com/Rohithburla51/SURAKSHANET-AI
