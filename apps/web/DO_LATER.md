# Orion — Pick Up Here

## What's Built
- `/home/ishan/Documents/Projects/orion-web` — Next.js 16 frontend (builds clean)
- `/home/ishan/Documents/Projects/orion_scaffold` — Python pipeline (60% done, core works)

## To Run Right Now

### Step 1 — Install Ollama + model
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:14b    # 9GB RAM — good balance
# or: qwen2.5:32b (better, 20GB), llama3.2:3b (tiny, any machine)
```

### Step 2 — Get free Tavily API key (web search)
- https://tavily.com → free tier → copy key
- Paste into `orion-web/.env.local` as `TAVILY_API_KEY=tvly-...`

### Step 3 — Run both services
```bash
# Terminal 1 — Python data pipeline
cd /home/ishan/Documents/Projects/orion_scaffold
pip install -r orion/requirements.txt
python -m orion.db.init_db
python -m orion.scripts.run_all

# Terminal 2 — Next.js dashboard
cd /home/ishan/Documents/Projects/orion-web
npm run dev
# → open localhost:3000
```

---

## For Production (zero cost)
Switch from Ollama to Google Gemini free tier (1M context, smarter):
1. Get free key at https://aistudio.google.com
2. In `orion-web/.env.local` set:
   ```
   AI_PROVIDER=google
   GOOGLE_AI_API_KEY=AIza...
   GOOGLE_MODEL=gemini-2.0-flash
   ```

---

## Next Build Tasks (in order)

### Task 2 — Connect to Neon Postgres (replace SQLite)
- Provision Neon DB at https://neon.tech (free tier)
- Get connection string
- Add to `orion-web/.env.local`: `DATABASE_URL=postgresql://...`
- Point Python pipeline at it: `DB_URL=postgresql://... python -m orion.db.init_db`
- Deploy Python pipeline to Railway: https://railway.app

### Task 3 — Deploy to Vercel
```bash
cd /home/ishan/Documents/Projects/orion-web
npx vercel --prod
# Add all env vars from .env.local in Vercel dashboard
```

### Task 4 — Graph visualization (Phase 2)
- Add interactive force-directed graph to dashboard
- `react-force-graph-2d` is already installed
- Show nodes colored by theme, edges with weights
- Click node → see all downstream assets

### Task 5 — Signal alerts (Phase 3)
- Email via Resend when new high-score signal appears
- Discord webhook option
- Scaffolded at `orion_scaffold/orion/signals/delivery.py`

### Task 6 — Auth + billing (Phase 3)
- Clerk already installed (`@clerk/nextjs`)
- Stripe already installed
- Free: 5 msgs/day, Pro $29/mo: unlimited, Trader $49/mo: API access

---

## Key Files Reference

| File | What it does |
|------|-------------|
| `orion-web/src/app/api/chat/route.ts` | AI chat endpoint — 4 tools, streaming |
| `orion-web/src/lib/ai-provider.ts` | Switch between Ollama / Google / Groq |
| `orion-web/src/lib/graph.ts` | Loads causal graph into AI context |
| `orion-web/src/lib/db.ts` | Neon Postgres queries |
| `orion-web/src/components/chat.tsx` | Chat UI (AI SDK v6 useChat) |
| `orion-web/src/app/dashboard/page.tsx` | Main dashboard layout |
| `orion_scaffold/orion/scripts/run_all.py` | Full pipeline orchestrator |
| `orion_scaffold/orion/config/graph.yaml` | 50-node causal graph |
| `orion_scaffold/orion/ui/app.py` | Python FastAPI (what-if endpoint) |

## AI SDK v6 Notes (broke from v5)
- `useChat` no longer takes `api:` — use `transport: new DefaultChatTransport({ api: '...' })`
- `handleSubmit` removed — use `sendMessage({ text })`
- `isLoading` removed — use `status === 'streaming' || status === 'submitted'`
- `parameters:` in `tool()` renamed to `inputSchema:`
- `toDataStreamResponse()` renamed to `toUIMessageStreamResponse()`
- `maxSteps:` removed — use `stopWhen: stepCountIs(N)`
- Tool parts: `tool-invocation` → `tool-{toolName}` (e.g. `tool-web_search`)
- Model IDs use dots not hyphens: `claude-sonnet-4.6` not `claude-sonnet-4-6`
