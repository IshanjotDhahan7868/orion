import { streamText, tool, stepCountIs } from 'ai'
import { z } from 'zod'
import { getAIModel } from '@/lib/ai-provider'
import { getGraphSystemPrompt, getNodeById } from '@/lib/graph'
import { getTopSignalsContext, getRecentEventsContext, getLatestSignals } from '@/lib/db'

export const runtime = 'nodejs'
export const maxDuration = 60

export async function POST(req: Request) {
  const { messages } = await req.json()

  // Fetch live context to inject into each request
  const [signalsCtx, eventsCtx] = await Promise.all([
    getTopSignalsContext(30).catch(() => 'Signals unavailable.'),
    getRecentEventsContext(20).catch(() => 'Events unavailable.'),
  ])

  const dynamicContext = `
## CURRENT SIGNAL SNAPSHOT (top 30 by score, last 7 days):
${signalsCtx}

## RECENT PARSED EVENTS (last 20):
${eventsCtx}
`

  const systemPrompt = getGraphSystemPrompt() + '\n\n' + dynamicContext

  const result = streamText({
    model: getAIModel(),
    system: systemPrompt,
    messages,
    stopWhen: stepCountIs(5),
    tools: {
      web_search: tool({
        description: 'Search the web for current news, data, or information relevant to the user\'s question. Use this for real-time context.',
        inputSchema: z.object({
          query: z.string().describe('Search query'),
        }),
        execute: async ({ query }) => {
          const apiKey = process.env.TAVILY_API_KEY
          if (!apiKey) return { error: 'Search unavailable (no API key)' }

          try {
            const res = await fetch('https://api.tavily.com/search', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                api_key: apiKey,
                query,
                search_depth: 'basic',
                max_results: 5,
                include_answer: true,
              }),
            })
            const data = await res.json()
            return {
              answer: data.answer,
              results: data.results?.map((r: { title: string; url: string; content: string }) => ({
                title: r.title,
                url: r.url,
                snippet: r.content?.slice(0, 300),
              })),
            }
          } catch (e) {
            return { error: `Search failed: ${e}` }
          }
        },
      }),

      run_what_if: tool({
        description: 'Run a what-if scenario: given an event description, propagate it through the causal graph and return ranked asset impacts. Use when user asks "what happens to X if Y".',
        inputSchema: z.object({
          event_text: z.string().describe('Description of the hypothetical event to propagate through the graph'),
        }),
        execute: async ({ event_text }) => {
          const engineUrl = process.env.ORION_ENGINE_URL || 'http://localhost:8000'
          try {
            const res = await fetch(`${engineUrl}/api/event`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ text: event_text, dry_run: true }),
            })
            const data = await res.json()
            return {
              events: data.events,
              signals: data.signals?.slice(0, 10),
              message: data.message,
            }
          } catch (e) {
            return { error: `Engine unavailable: ${e}. The Python pipeline may not be running.` }
          }
        },
      }),

      build_portfolio: tool({
        description: 'Build a capped portfolio recommendation from the highest conviction ORION signals. Use when the user asks how to size or allocate across current opportunities.',
        inputSchema: z.object({
          limit: z.number().optional().describe('How many candidate assets to consider before caps are applied'),
          min_score: z.number().optional().describe('Minimum adjusted score required to include a signal'),
          gross_exposure: z.number().optional().describe('Target gross exposure from 0 to 1'),
          max_per_asset: z.number().optional().describe('Maximum portfolio weight for a single asset'),
          max_per_theme: z.number().optional().describe('Maximum portfolio weight for a single theme'),
          confirmed_only: z.boolean().optional().describe('Whether to exclude unconfirmed signals'),
        }),
        execute: async ({
          limit = 12,
          min_score = 0,
          gross_exposure = 1,
          max_per_asset = 0.1,
          max_per_theme = 0.3,
          confirmed_only = true,
        }) => {
          const engineUrl = process.env.ORION_ENGINE_URL || 'http://localhost:8000'
          try {
            const res = await fetch(`${engineUrl}/api/portfolio/recommendation`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                limit,
                min_score,
                gross_exposure,
                max_per_asset,
                max_per_theme,
                confirmed_only,
              }),
            })
            const data = await res.json()
            return data
          } catch (e) {
            return { error: `Portfolio engine unavailable: ${e}` }
          }
        },
      }),

      lookup_signals: tool({
        description: 'Look up current signals from the ORION engine or local signal artifacts, optionally filtered by asset.',
        inputSchema: z.object({
          asset: z.string().optional().describe('Ticker symbol or asset name to filter by (e.g. NVDA, COPPER)'),
          limit: z.number().optional().describe('Number of signals to return (default 20)'),
        }),
        execute: async ({ asset, limit = 20 }) => {
          try {
            const signals = await getLatestSignals(100)
            const filtered = asset
              ? signals.filter(s => s.asset?.toUpperCase().includes(asset.toUpperCase()))
              : signals
            return {
              signals: filtered.slice(0, limit).map(s => ({
                asset: s.asset,
                score: s.adjusted_score,
                path: s.why_path,
                lag_months: s.when_months,
                confirmed: s.confirmed,
                risks: s.risk_flags_json,
                event_type: s.event_type,
                created_at: s.created_at,
              })),
              count: filtered.length,
            }
          } catch (e) {
            return { error: `Signals unavailable: ${e}` }
          }
        },
      }),

      lookup_graph_node: tool({
        description: 'Get detailed information about a specific node in the causal graph — what it represents, what affects it, and connected assets.',
        inputSchema: z.object({
          node_id: z.string().describe('The node ID from the graph (e.g. AI_Compute_Demand, Copper, Defense_Spending)'),
        }),
        execute: async ({ node_id }) => {
          const node = getNodeById(node_id)
          if (!node) {
            return { error: `Node "${node_id}" not found. Check spelling or try a related node name.` }
          }
          return {
            id: node.id,
            theme: node.theme,
            type: node.type,
            description: node.what_is_this,
            what_affects_it: node.what_affects_it,
            assets: node.assets,
          }
        },
      }),
    },
  })

  return result.toUIMessageStreamResponse()
}
