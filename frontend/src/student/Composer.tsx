import { Mic, MicOff, SendHorizontal } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { Kbd } from "../components/ui";

export const MAX_QUESTION = 500; // the API's limit

// The browser's own speech recognition (Chrome, Edge). Nothing is recorded by CampusMate.
interface Recognition {
  lang: string;
  interimResults: boolean;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}
type RecognitionConstructor = new () => Recognition;
const SpeechRecognition = (globalThis as unknown as { webkitSpeechRecognition?: RecognitionConstructor; SpeechRecognition?: RecognitionConstructor })
  .SpeechRecognition ?? (globalThis as unknown as { webkitSpeechRecognition?: RecognitionConstructor }).webkitSpeechRecognition;

export function Composer({ onAsk, busy }: { onAsk: (question: string) => void; busy: boolean }) {
  const [text, setText] = useState("");
  const [listening, setListening] = useState(false);
  const recognition = useRef<Recognition | null>(null);
  const question = text.trim();
  const ready = question.length >= 2 && !busy;

  useEffect(() => () => recognition.current?.stop(), []);

  function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!ready) return;
    onAsk(question);
    setText("");
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {  // Shift+Enter starts a new line
      event.preventDefault();
      submit();
    }
  }

  function toggleVoice() {
    if (!SpeechRecognition) return;
    if (listening) { recognition.current?.stop(); return; }
    const r = new SpeechRecognition();
    r.lang = "en-IN";
    r.interimResults = false;
    r.onresult = (event) => setText((t) => `${t} ${event.results[0][0].transcript}`.trim().slice(0, MAX_QUESTION));
    r.onend = () => setListening(false);
    recognition.current = r;
    setListening(true);
    r.start();
  }

  return (
    <div className="border-t border-line-2 bg-gradient-to-t from-panel via-panel/95 to-panel/40 p-3.5 sm:p-4">
      <form onSubmit={submit} className="relative flex items-end">
        <label htmlFor="question" className="sr-only">Your question</label>
        <textarea id="question" rows={1} value={text} maxLength={MAX_QUESTION} onKeyDown={onKeyDown}
                  onChange={(event) => setText(event.target.value)}
                  placeholder="Ask anything about courses, credits, electives, faculty, labs, policies or the calendar..."
                  className="max-h-40 min-h-12 w-full resize-none rounded-2xl border border-line bg-panel py-3 pl-4 pr-24 text-sm text-ink shadow-sm outline-none transition
                             [field-sizing:content] placeholder:text-ink-4 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20" />
        <div className="absolute bottom-2 right-2.5 flex items-center gap-1.5">
          {text.length > MAX_QUESTION - 60 && <span className="text-[10px] text-ink-4">{MAX_QUESTION - text.length}</span>}
          {SpeechRecognition && (
            <button type="button" onClick={toggleVoice} aria-label={listening ? "Stop dictation" : "Dictate your question"}
                    className={`rounded-lg p-1.5 transition ${listening ? "bg-rose-500/10 text-rose-600" : "text-ink-4 hover:bg-panel-3 hover:text-ink-2"}`}>
              {listening ? <MicOff size={16} /> : <Mic size={16} />}
            </button>
          )}
          <button type="submit" disabled={!ready} aria-label="Ask"
                  className="grid h-8 w-8 place-items-center rounded-xl bg-solid text-solid-ink shadow-sm transition hover:bg-blue-600 hover:text-white active:scale-90 disabled:opacity-30 disabled:hover:bg-solid disabled:hover:text-solid-ink">
            <SendHorizontal size={15} strokeWidth={2.4} />
          </button>
        </div>
      </form>
      <div className="mt-2 flex items-center justify-between px-1 text-[10px] font-medium text-ink-4">
        <span>Grounded in CampusMate’s verified knowledge base · synthetic demo data is always labelled</span>
        <span className="hidden sm:inline">Press <Kbd>Return ↵</Kbd> to submit</span>
      </div>
    </div>
  );
}
