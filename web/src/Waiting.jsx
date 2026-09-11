import { useEffect, useState } from "react";

import { API } from "./api";

export default function Waiting({ sid, onReady, onReset }) {
  const [status, setStatus] = useState({ state: "queued", done: 0, total: 0 });

  useEffect(() => {
    const id = setInterval(async () => {
      const r = await fetch(`${API}/status/${sid}`);
      const s = await r.json();
      setStatus(s);
      if (s.state === "ready") {
        clearInterval(id);
        onReady();
      }
    }, 1500);
    return () => clearInterval(id);
  }, [sid, onReady]);

  if (String(status.state).startsWith("error")) {
    return (
      <div className="stage">
        <p className="question">That file didn't read as a Letterboxd export.</p>
        <button className="quiet" onClick={onReset}>Start over</button>
      </div>
    );
  }

  return (
    <div className="stage">
      <p className="question">Looking up your films</p>
      <p className="lede">
        Matching each one to its director, genres, and poster. Takes about a minute.
      </p>
      {status.total > 0 && (
        <p className="progress">{status.done} of {status.total}</p>
      )}
    </div>
  );
}