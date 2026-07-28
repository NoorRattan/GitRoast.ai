"use client";

import { ShieldOff, Undo2 } from "lucide-react";
import { useState } from "react";
import { optOut, undoOptOut } from "@/lib/api-client";

export function OptOutControl({
  username,
  initialOptedOut = false
}: {
  username: string;
  initialOptedOut?: boolean;
}): JSX.Element {
  const [isOptedOut, setIsOptedOut] = useState(initialOptedOut);
  const [isPending, setIsPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function updateOptOut(next: boolean): Promise<void> {
    setIsPending(true);
    setMessage(null);
    try {
      if (next) {
        await optOut(username);
      } else {
        await undoOptOut(username);
      }
      setIsOptedOut(next);
      setMessage(next ? "Future audits and cards are now hidden." : "Audits are available again.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The privacy setting could not be updated.");
    } finally {
      setIsPending(false);
    }
  }

  return (
    <section className="panel opt-out-panel" aria-labelledby="privacy-title">
      <div>
        <h2 id="privacy-title">Profile privacy</h2>
        <p className="muted">
          This is self-service. If you are not the owner, the real owner can opt back in the same way.
        </p>
      </div>
      <button
        className="button"
        type="button"
        disabled={isPending}
        onClick={() => void updateOptOut(!isOptedOut)}
      >
        {isOptedOut ? <Undo2 aria-hidden="true" size={17} /> : <ShieldOff aria-hidden="true" size={17} />}
        {isOptedOut ? "Undo opt-out" : "Opt this profile out"}
      </button>
      {message ? <p className="form-message" role="status">{message}</p> : null}
    </section>
  );
}
