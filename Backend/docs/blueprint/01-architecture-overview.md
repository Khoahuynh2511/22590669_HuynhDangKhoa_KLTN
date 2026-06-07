# 01 — Architecture Overview

## Hybrid Multi-Agent Architecture

Sub-agent cho tư vấn, workflow cứng cho giao dịch, event jobs cho tác vụ chủ động.

```text
┌──────────────────────────────────────────────────────────────┐
│                     FRONTEND — Angular 19                    │
│                                                              │
│  ai-chatbot     ai-chat-panel     admin-chatbot     pages    │
│  Tour AI        News Agent        Admin SQL         Booking  │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ SSE /chat/stream + REST /api/v1/*
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                      BACKEND — FastAPI                       │
│                                                              │
│  /chat/stream  -> AgentRouter                                │
│  /api/v1/*     -> Routers: bookings, payments, flights...    │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│              SUPERVISORGRAPH / ORCHESTRATOR                  │
│                     LangGraph main graph                     │
│                                                              │
│  1. CustomerQueryAgent — parse intent, extract slots         │
│  2. RouteToSpecialist — chọn sub-agent hoặc workflow         │
│  3. ReplySynthesizer — gom output, trả lời tiếng Việt       │
└───────┬──────────────┬──────────────┬──────────────┬────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│Recommendation│ │ Itinerary    │ │ FlightAgent  │ │ HotelAgent   │
│Agent         │ │ Agent        │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘

┌──────────────┐ ┌────────────────────┐ ┌───────────────┐ ┌──────────────┐
│TransportAgent│ │BookingPaymentFlow  │ │NewsSearchAgent│ │AdminGraph    │
│              │ │State Machine       │ │               │ │              │
└──────────────┘ └────────────────────┘ └───────────────┘ └──────────────┘

                            │
                            │ StructuredTool / fastmcp.Client
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    FASTMCP COMPOSITE SERVER                  │
│                           /mcp                               │
│                                                              │
│  booking_mcp | tour_search_mcp | itinerary_mcp | flight_mcp │
│  hotel_mcp | transport_mcp | weather_mcp | personalization   │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                     EXTERNAL / STORAGE                       │
│                                                              │
│ Supabase pgvector | Redis | Mem0 | FalkorDB | Cloudinary     │
│ OpenWeatherMap | AviationStack | Amadeus | Booking API       │
│ 12Go / Baolau | Perplexity | SendGrid | VNPay                │
└──────────────────────────────────────────────────────────────┘
```

## Core Design Decision — Hybrid

| Task type | Pattern | Lý do |
|---|---|---|
| Advisory / Creative | Specialist Sub-agents | Cần reasoning, flexibility |
| Transactional / Money | Deterministic Workflow | Cần idempotent, audit, không hallucinate |
| Proactive / Scheduled | Event-driven Jobs | Không block chat, chạy background |
| Tool execution | FastMCP | Chuẩn hóa, composable, testable |
| Storage + memory | Supabase + Redis + Mem0 + FalkorDB | Shared state layer |

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Angular 19, PrimeNG 19, TailwindCSS |
| Backend | FastAPI, LangGraph, LangChain, FastMCP |
| AI/LLM | OpenAI gpt-5-mini (qua LangChain) |
| Vector/Memory | Supabase pgvector + Mem0 + FalkorDB/Graphiti |
| Tools | FastMCP server (`@mcp.tool()`) |
| Payment | VNPay |
| Auth | JWT + Google OAuth |
| Flight | AviationStack (search) + Amadeus (booking) |
