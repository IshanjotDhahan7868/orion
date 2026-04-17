'use client'

import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'
import { useEffect, useRef, useState } from 'react'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { MessageResponse } from '@/components/ai-elements/message'

const TOOL_LABELS: Record<string, string> = {
  web_search: '⟳ searching web...',
  run_what_if: '⟳ propagating through graph...',
  build_portfolio: '⟳ sizing portfolio...',
  lookup_signals: '⟳ querying signals...',
  lookup_graph_node: '⟳ looking up node...',
}

function ToolCallIndicator({ toolName }: { toolName: string }) {
  return (
    <div className="text-xs text-zinc-500 italic pl-2 border-l border-zinc-700">
      {TOOL_LABELS[toolName] ?? `⟳ ${toolName}...`}
    </div>
  )
}

export function OrionChat() {
  const { messages, sendMessage, status } = useChat({
    transport: new DefaultChatTransport({ api: '/api/chat' }),
  })

  const [input, setInput] = useState('')
  const isActive = status === 'streaming' || status === 'submitted'
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function submit() {
    const text = input.trim()
    if (!text || isActive) return
    setInput('')
    sendMessage({ text })
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <ScrollArea className="flex-1 p-4">
        {messages.length === 0 && (
          <div className="text-zinc-500 text-sm space-y-2 p-4">
            <p className="text-zinc-300 font-semibold">ORION v1.0 — Causal Macro Intelligence</p>
            <p>Ask me anything about macro events and asset impacts:</p>
            <div className="space-y-1 text-zinc-600 text-xs mt-3">
              <p>→ &quot;What happens to copper if China restricts rare earth exports?&quot;</p>
              <p>→ &quot;Show me current signals for semiconductor stocks&quot;</p>
              <p>→ &quot;Build me a capped portfolio from the top confirmed ORION signals&quot;</p>
              <p>→ &quot;What are the top signals this week?&quot;</p>
              <p>→ &quot;Explain the AI_Compute_Demand node and its downstream effects&quot;</p>
              <p>→ &quot;What did OPEC announce recently?&quot;</p>
            </div>
          </div>
        )}

        <div className="space-y-4">
          {messages.map(m => (
            <div key={m.id}>
              {m.role === 'user' ? (
                <div className="flex gap-2">
                  <span className="text-emerald-500 text-xs mt-0.5 shrink-0">›</span>
                  <div className="space-y-1 flex-1">
                    {m.parts.map((part, i) =>
                      part.type === 'text' ? (
                        <p key={i} className="text-zinc-100 text-sm">{part.text}</p>
                      ) : null
                    )}
                  </div>
                </div>
              ) : (
                <div className="flex gap-2">
                  <span className="text-blue-400 text-xs mt-0.5 shrink-0 font-bold">⬡</span>
                  <div className="flex-1 space-y-2">
                    {m.parts.map((part, i) => {
                      if (part.type === 'text' && part.text) {
                        return (
                          <MessageResponse key={i} className="text-zinc-300 text-sm leading-relaxed prose-invert prose-sm max-w-none">
                            {part.text}
                          </MessageResponse>
                        )
                      }
                      // tool-{name} parts — show indicator while input is being built
                      if (part.type.startsWith('tool-')) {
                        const toolName = part.type.slice(5) // strip "tool-" prefix
                        const isInProgress =
                          'state' in part &&
                          (part.state === 'input-streaming' || part.state === 'input-available')
                        if (isInProgress) {
                          return <ToolCallIndicator key={i} toolName={toolName} />
                        }
                      }
                      return null
                    })}
                  </div>
                </div>
              )}
            </div>
          ))}

          {isActive && (
            <div className="flex gap-2">
              <span className="text-blue-400 text-xs mt-0.5 shrink-0 font-bold">⬡</span>
              <div className="flex gap-1 items-center pt-1">
                <span className="w-1 h-1 bg-zinc-500 rounded-full animate-pulse" />
                <span className="w-1 h-1 bg-zinc-500 rounded-full animate-pulse delay-75" />
                <span className="w-1 h-1 bg-zinc-500 rounded-full animate-pulse delay-150" />
              </div>
            </div>
          )}

          {status === 'error' && (
            <div className="text-red-400 text-xs border border-red-500/30 bg-red-500/10 rounded p-2">
              Something went wrong. Try again.
            </div>
          )}
        </div>
        <div ref={bottomRef} />
      </ScrollArea>

      {/* Input */}
      <div className="border-t border-zinc-800 p-3">
        <div className="flex gap-2 items-end">
          <Textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Ask about macro events, signals, or what-if scenarios..."
            className="flex-1 bg-zinc-900 border-zinc-700 text-zinc-100 placeholder:text-zinc-600 text-sm resize-none min-h-[40px] max-h-[120px] font-mono focus-visible:ring-zinc-600"
            rows={1}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                submit()
              }
            }}
          />
          <button
            type="button"
            onClick={submit}
            disabled={isActive || !input.trim()}
            className="px-3 py-2 text-xs font-mono bg-zinc-800 hover:bg-zinc-700 disabled:opacity-40 disabled:cursor-not-allowed text-zinc-300 rounded border border-zinc-700 transition-colors whitespace-nowrap"
          >
            {isActive ? '...' : 'send ↵'}
          </button>
        </div>
        <p className="text-zinc-700 text-xs mt-1.5">Shift+Enter for newline · Enter to send</p>
      </div>
    </div>
  )
}
