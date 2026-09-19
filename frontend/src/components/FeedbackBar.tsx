import { ThumbsDown, ThumbsUp } from "lucide-react";
import { useState } from "react";

import { api } from "../api/client";
import type { Rating } from "../api/types";

type Saved = { rating: Rating; comment: string | null };

// One rating per answer, stored with the exact sources that produced it. Rating again replaces it.
export function FeedbackBar({ queryId }: { queryId: string }) {
  const [saved, setSaved] = useState<Saved | null>(null);
  const [draft, setDraft] = useState<Rating | null>(null);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function send(rating: Rating, text?: string) {
    setError(null);
    try {
      const result = await api.feedback(queryId, rating, text);
      setSaved({ rating: result.rating, comment: result.comment });
      setDraft(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Feedback could not be saved.");
    }
  }

  const button = (rating: Rating) =>
    `grid h-7 w-7 place-items-center rounded-md hover:bg-sunken ${saved?.rating === rating ? "text-accent" : "text-ink-3"}`;

  return (
    <div className="mt-3 text-xs text-ink-3">
      <div className="flex items-center gap-1">
        <span className="mr-1">{saved ? "Thanks, your feedback is saved." : "Was this answer right?"}</span>
        <button type="button" aria-label="Good answer" aria-pressed={saved?.rating === "up"} className={button("up")}
                onClick={() => void send("up")}><ThumbsUp size={14} aria-hidden /></button>
        <button type="button" aria-label="Wrong or unhelpful answer" aria-pressed={saved?.rating === "down"}
                className={button("down")} onClick={() => setDraft("down")}><ThumbsDown size={14} aria-hidden /></button>
      </div>
      {draft === "down" && (
        <form className="mt-2 flex gap-2" onSubmit={(event) => { event.preventDefault(); void send("down", comment); }}>
          <label htmlFor={`comment-${queryId}`} className="sr-only">What was wrong?</label>
          <input id={`comment-${queryId}`} value={comment} maxLength={1000} onChange={(e) => setComment(e.target.value)}
                 placeholder="What was wrong? (optional)"
                 className="flex-1 rounded-md border border-line bg-surface px-2 py-1.5 text-sm text-ink outline-none
                            focus:border-accent" />
          <button type="submit" className="rounded-md bg-ink px-3 text-sm text-white">Send</button>
        </form>
      )}
      {error && <p role="alert" className="mt-1 text-danger">{error}</p>}
    </div>
  );
}
