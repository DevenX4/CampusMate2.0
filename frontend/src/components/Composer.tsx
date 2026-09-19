import { ArrowUp } from "lucide-react";
import { useState, type FormEvent, type KeyboardEvent } from "react";

export const MAX_QUESTION = 500; // the API's limit

export function Composer({ onAsk, busy }: { onAsk: (question: string) => void; busy: boolean }) {
  const [text, setText] = useState("");
  const question = text.trim();
  const ready = question.length >= 2 && !busy;

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

  return (
    <form onSubmit={submit}
          className="flex items-end gap-2 rounded-xl border border-line bg-surface p-2 pl-4 shadow-float
                     focus-within:ring-[1.5px] focus-within:ring-accent">
      <label htmlFor="question" className="sr-only">Your question</label>
      <textarea id="question" rows={1} value={text} maxLength={MAX_QUESTION}
                onChange={(event) => setText(event.target.value)} onKeyDown={onKeyDown}
                placeholder="Ask about courses, credits, electives, faculty, labs, policies or the calendar..."
                className="max-h-40 min-h-10 flex-1 resize-none bg-transparent py-2 text-[15px] outline-none
                           [field-sizing:content] placeholder:text-ink-3" />
      {text.length > MAX_QUESTION - 50 && (
        <span className="pb-2.5 text-xs text-ink-3">{MAX_QUESTION - text.length}</span>
      )}
      <button type="submit" disabled={!ready} aria-label="Ask"
              className="grid h-10 w-10 place-items-center rounded-lg bg-accent text-white transition-opacity
                         disabled:opacity-30">
        <ArrowUp size={18} aria-hidden />
      </button>
    </form>
  );
}
