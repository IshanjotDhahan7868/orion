/**
 * Configurable AI provider for Orion.
 *
 * Set AI_PROVIDER in .env.local to switch:
 *   AI_PROVIDER=ollama    → Ollama local (default, free)
 *   AI_PROVIDER=google    → Google Gemini (free tier, 1M context)
 *   AI_PROVIDER=groq      → Groq (free tier, fast)
 *
 * Model overrides:
 *   OLLAMA_MODEL=gemma3:4b            (default: gemma3:4b)
 *   GOOGLE_MODEL=gemini-2.0-flash     (default: gemini-2.0-flash)
 *   GROQ_MODEL=llama-3.3-70b-versatile
 */

import { createOpenAICompatible } from '@ai-sdk/openai-compatible'
import { createGoogleGenerativeAI } from '@ai-sdk/google'
import { createGroq } from '@ai-sdk/groq'
import type { LanguageModel } from 'ai'

export function getAIModel(): LanguageModel {
  const provider = process.env.AI_PROVIDER ?? 'ollama'

  switch (provider) {
    case 'google': {
      const apiKey = process.env.GOOGLE_AI_API_KEY
      if (!apiKey) throw new Error('GOOGLE_AI_API_KEY is required for AI_PROVIDER=google')
      const g = createGoogleGenerativeAI({ apiKey })
      const model = process.env.GOOGLE_MODEL ?? 'gemini-2.0-flash'
      return g(model)
    }

    case 'groq': {
      const apiKey = process.env.GROQ_API_KEY
      if (!apiKey) throw new Error('GROQ_API_KEY is required for AI_PROVIDER=groq')
      const g = createGroq({ apiKey })
      const model = process.env.GROQ_MODEL ?? 'llama-3.3-70b-versatile'
      return g(model)
    }

    case 'ollama':
    default: {
      // Ollama exposes an OpenAI-compatible API at /v1
      const baseURL = process.env.OLLAMA_BASE_URL ?? 'http://localhost:11434/v1'
      const g = createOpenAICompatible({ name: 'ollama', baseURL })
      const model = process.env.OLLAMA_MODEL ?? 'gemma3:4b'
      return g(model)
    }
  }
}
