import fs from 'fs'
import path from 'path'
import yaml from 'js-yaml'

export interface GraphNode {
  id: string
  theme: string
  type: string
  what_is_this: string
  what_affects_it?: string[]
  assets?: { equities?: string[]; etfs?: string[]; commodities?: string[] }
}

export interface GraphEdge {
  from: string
  to: string
  weight: number
  lag_months: number
  confidence: number
}

interface GraphData {
  version: string
  themes: string[]
  nodes: GraphNode[]
  edges: GraphEdge[]
}

let _cached: string | null = null

function getRepoRoot(): string {
  if (process.env.ORION_ROOT_DIR) return process.env.ORION_ROOT_DIR
  return path.resolve(/* turbopackIgnore: true */ process.cwd(), '..', '..')
}

function readYamlFile(candidates: string[]): string {
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return fs.readFileSync(candidate, 'utf-8')
    }
  }
  throw new Error(`Unable to find YAML file. Tried: ${candidates.join(', ')}`)
}

function loadGraphYaml(): GraphData {
  const root = getRepoRoot()
  const raw = readYamlFile([
    path.join(root, 'config/graph.yaml'),
    path.join(process.cwd(), 'src/data/graph.yaml'),
  ])
  return yaml.load(raw) as GraphData
}

function loadAssetsYaml(): Record<string, { type: string; nodes: string[] }> {
  const root = getRepoRoot()
  const raw = readYamlFile([
    path.join(root, 'config/assets.yaml'),
    path.join(process.cwd(), 'src/data/assets.yaml'),
  ])
  return yaml.load(raw) as Record<string, { type: string; nodes: string[] }>
}

export function getAssetMappings(): Record<string, { type: string; nodes: string[] }> {
  return loadAssetsYaml()
}

export function getGraphSystemPrompt(): string {
  if (_cached) return _cached

  const graph = loadGraphYaml()
  const assets = loadAssetsYaml()

  const nodeLines = graph.nodes
    .map(n => `  ${n.id} [${n.theme}/${n.type}]: ${n.what_is_this}`)
    .join('\n')

  const edgeLines = graph.edges
    .map(e => `  ${e.from} → ${e.to} (weight=${e.weight}, lag=${e.lag_months}mo, conf=${e.confidence})`)
    .join('\n')

  const assetLines = Object.entries(assets)
    .map(([ticker, a]) => `  ${ticker} [${a.type}]: nodes=[${a.nodes.join(', ')}]`)
    .join('\n')

  _cached = `You are ORION, an AI macro-signal analyst. You reason about how real-world events (geopolitical, economic, policy) propagate through a causal graph to affect asset prices.

You have access to a live causal dependency graph. When an event occurs, it "seeds" one or more nodes, and impact propagates through edges with weights and time lags. You explain these causal chains clearly and help users understand which assets are likely affected and why.

ORION's philosophy:
- Macro-signal investing, NOT day trading or price prediction
- Causal modeling: first/second/third-order effects with realistic time lags (weeks to years)
- Every signal has an explainable causal chain
- You never give financial advice — you provide analytical frameworks and causal reasoning

## CAUSAL GRAPH (v${graph.version})
Themes: ${graph.themes.join(', ')}

### Nodes (${graph.nodes.length} total):
${nodeLines}

### Edges (${graph.edges.length} total):
${edgeLines}

## ASSET-TO-NODE MAPPINGS:
${assetLines}

## How to use your tools:
- Use \`web_search\` when you need current news or data to answer a question
- Use \`run_what_if\` when user asks "what happens if X" — this runs full BFS propagation through the graph
- Use \`lookup_signals\` to retrieve current signals from the database
- Use \`lookup_graph_node\` to get detailed info on any graph node

Always show your reasoning. When explaining impacts, trace the causal path explicitly: "Event seeds NodeA → NodeB (lag Xmo, weight Y) → NodeC (lag Zmo) → affects TICKER".`

  return _cached
}

export function getGraphNodes(): GraphNode[] {
  return loadGraphYaml().nodes
}

export function getGraphEdges(): GraphEdge[] {
  return loadGraphYaml().edges
}

export function getNodeById(nodeId: string): GraphNode | undefined {
  return loadGraphYaml().nodes.find(n => n.id === nodeId)
}
