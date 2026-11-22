// Transport for the student chat: SSE over fetch, with a JSON fallback.

const STEP_KEYS = ['understand', 'search', 'read', 'write'];

// The local fallback engine sends numbered steps with internal wording.
const STEP_LABELS = {
  understand: 'Understanding your question',
  search: 'Searching campus records',
  read: 'Reading matching records',
  write: 'Writing the answer',
};

export const STAGE_MOOD = {
  understand: 'thinking',
  search: 'searching',
  read: 'reading',
  write: 'writing',
};

const OUTAGE_ROUTE = 'service_unavailable';
const OUTAGE_PROVIDER = 'CampusMate Service Monitor';
const MAX_HISTORY_TURNS = 12;

export class ChatError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'ChatError';
    this.code = code; // 'network' | 'unavailable' | 'interrupted'
  }
}

export const isAbort = (err) => err?.name === 'AbortError';

function parseFrame(frame) {
  let event = 'message';
  const dataLines = [];
  for (const line of frame.split(/\r\n|\n|\r/)) {
    if (!line || line.startsWith(':')) continue;
    const colon = line.indexOf(':');
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? '' : line.slice(colon + 1);
    if (value.startsWith(' ')) value = value.slice(1);
    if (field === 'event') event = value;
    else if (field === 'data') dataLines.push(value);
  }
  if (!dataLines.length) return null;
  try {
    return { event, data: JSON.parse(dataLines.join('\n')) };
  } catch {
    return null;
  }
}

/** Reads an SSE body, holding back partial frames and multi-byte characters split across reads. */
export async function readSSE(body, onEvent) {
  const reader = body.getReader();
  const decoder = new TextDecoder('utf-8');
  const boundary = /\r\n\r\n|\n\n|\r\r/;
  let buffer = '';

  const drain = () => {
    let match = boundary.exec(buffer);
    while (match) {
      const parsed = parseFrame(buffer.slice(0, match.index));
      buffer = buffer.slice(match.index + match[0].length);
      if (parsed) onEvent(parsed);
      match = boundary.exec(buffer);
    }
  };

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      drain();
    }
    buffer += decoder.decode();
    drain();
    if (buffer.trim()) {
      const parsed = parseFrame(buffer);
      if (parsed) onEvent(parsed);
    }
  } finally {
    reader.releaseLock?.();
  }
}

function safeLinks(links) {
  if (!Array.isArray(links)) return [];
  return links.filter((link) => {
    try {
      return link?.label && ['http:', 'https:'].includes(new URL(link.url).protocol);
    } catch {
      return false;
    }
  });
}

/** Keeps the answer text byte-exact: the backend matches follow-ups against it. */
function normalizeFinal(raw) {
  const sources = (Array.isArray(raw?.sources) ? raw.sources : [])
    .filter((s) => s && s.cited !== false)
    .map((s, index) => ({
      ref: s.ref ?? index + 1,
      title: s.title || s.label || 'Campus record',
      content: s.content || s.text || '',
      source_type: s.source_type || '',
    }));

  return {
    text: raw?.answer ?? raw?.text ?? '',
    sources,
    route: raw?.route || '',
    answer_type: raw?.answer_type || '',
    provider: raw?.provider || '',
    clarification_required: Boolean(raw?.clarification_required),
    options: Array.isArray(raw?.options) ? raw.options.filter(Boolean).map(String) : [],
    links: safeLinks(raw?.links),
    grounding: raw?.grounding || null,
    timings_ms: raw?.timings_ms || null,
  };
}

const isUsable = (final) => Boolean(final?.text?.trim()) && final.route !== OUTAGE_ROUTE;

async function requestDirect(payload, signal) {
  let res;
  try {
    res = await fetch('/api/chat/direct', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      signal,
      body: JSON.stringify(payload),
    });
  } catch (err) {
    if (isAbort(err)) throw err;
    throw new ChatError('network', 'CampusMate could not be reached. Check your connection and try again.');
  }

  let data = null;
  try {
    data = await res.json();
  } catch (err) {
    if (isAbort(err)) throw err;
  }

  const final = data ? normalizeFinal(data) : null;
  if (!res.ok || !isUsable(final)) {
    throw new ChatError('unavailable', 'The answer engine is unavailable right now, so this question was not checked against campus records.');
  }
  return final;
}

function normalizeStage(data) {
  const key = data?.key || STEP_KEYS[data?.step];
  if (!key) return null;
  return { key, label: data.key ? data.label || STEP_LABELS[key] : STEP_LABELS[key], count: data.count };
}

/**
 * Streams one answer. Resolves with the final payload; rejects with AbortError or ChatError.
 * A stream that dies before any text falls back to /api/chat/direct.
 */
export async function requestAnswer({ question, conversationId, history, signal, onStage, onToken, onFallback }) {
  const payload = { question, conversation_id: conversationId, history };
  let res = null;

  try {
    res = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      credentials: 'include',
      signal,
      body: JSON.stringify(payload),
    });
  } catch (err) {
    if (isAbort(err)) throw err;
  }

  let final = null;
  let sawToken = false;

  if (res?.ok && res.body) {
    try {
      await readSSE(res.body, ({ event, data }) => {
        if (event === 'stage') {
          const stage = normalizeStage(data);
          if (stage) onStage?.(stage);
        } else if (event === 'token') {
          const text = data?.text ?? data?.delta ?? '';
          if (text) {
            sawToken = true;
            onToken?.(text);
          }
        } else if (event === 'done') {
          final = normalizeFinal(data);
        }
      });
    } catch (err) {
      if (isAbort(err)) throw err;
    }
  }

  if (isUsable(final)) return final;
  if (sawToken) throw new ChatError('interrupted', 'The connection dropped before the answer finished.');

  onFallback?.();
  return requestDirect(payload, signal);
}

/** Builds request history from saved messages, leaving out failed turns. */
export function toHistory(list) {
  const turns = [];
  list.forEach((message, index) => {
    if (message.sender !== 'user' && message.sender !== 'assistant') return;
    if (!message.text) return;
    if (message.sender === 'assistant' && isFailedMessage(message)) return;
    if (message.sender === 'user' && list[index + 1] && isFailedMessage(list[index + 1])) return;
    turns.push({ role: message.sender, content: message.text });
  });
  return turns.slice(-MAX_HISTORY_TURNS);
}

export function isFailedMessage(message) {
  return message?.sender === 'assistant'
    && (message.status === 'error' || message.provider === OUTAGE_PROVIDER || message.route === OUTAGE_ROUTE);
}
