import { useState } from "react";

const API = "http://127.0.0.1:8000";

export default function Landing({ onSession }) {
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState(null);

  async function send(file) {
    if (!file) return;
    if (!file.name.endsWith(".zip")) {
      setError("That's not a .zip — upload the file Letterboxd gave you, unopened.");
      return;
    }

    setError(null);
    const body = new FormData();
    body.append("file", file);

    try {
      const r = await fetch(`${API}/upload`, { method: "POST", body });
      if (!r.ok) throw new Error();
      const { session_id } = await r.json();
      onSession(session_id);
    } catch {
      setError("Upload didn't go through. Try again.");
    }
  }

  return (
    <div className="stage landing">
      <h1 className="pitch">
        Your star ratings say what you'd defend.
        <br />
        This finds what you actually love.
      </h1>

      <p className="lede">
        Answer a few head-to-heads between films you've seen, and get a ranking
        built from your choices instead of your ratings — plus the directors and
        genres behind it.
      </p>

      <div
        className={`drop ${dragging ? "over" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          send(e.dataTransfer.files[0]);
        }}
      >
        <label className="droplabel">
          Drop your Letterboxd export here, or choose a file
          <input
            type="file"
            accept=".zip"
            onChange={(e) => send(e.target.files[0])}
          />
        </label>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="howto">
        <p className="section-label">Getting your file</p>
        <ol>
          <li>
            Open{" "}
            <a href="https://letterboxd.com/settings/data" target="_blank" rel="noreferrer">
              letterboxd.com/settings/data
            </a>{" "}
            and choose Export your data.
          </li>
          <li>Letterboxd emails you a .zip, or downloads it straight away.</li>
          <li>Drop it above without unzipping it.</li>
        </ol>
        <p className="fineprint">
          Export only works on the Letterboxd website, not the phone apps. Your
          file stays on this server only long enough to read your films — the
          part with your name and email is deleted on upload.
        </p>
      </div>
    </div>
  );
}