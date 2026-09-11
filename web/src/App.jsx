import { useEffect, useState, useCallback } from "react";
import Results from "./Results";

import { API } from "./api";

import Landing from "./Landing";
import Waiting from "./Waiting";

const KEY = "rmm.session";

export default function App() {
  const [sid, setSid] = useState(() => localStorage.getItem(KEY));
  const [ready, setReady] = useState(false);
  const [pair, setPair] = useState(null);
  const [next, setNext] = useState(null);
  const [view, setView] = useState("compare");
  const [count, setCount] = useState(0);

  const fetchPair = useCallback(async () => {
    const r = await fetch(`${API}/pair/${sid}`);
    return r.json();
  }, [sid]);

  useEffect(() => {
    if (!sid || !ready) return;
    fetchPair().then((first) => {
      setPair(first);
      setCount(first.count);
      fetchPair().then(setNext);
    });
  }, [fetchPair, sid, ready]);

  useEffect(() => {
    if (!next || next.done) return;
    [next.a, next.b].forEach((f) => {
      if (f.poster) new Image().src = f.poster;
    });
  }, [next]);

  function advance() {
    setPair(next);
    setNext(null);
    fetchPair().then(setNext);
  }

  function choose(winner) {
    if (!pair || pair.done) return;

    fetch(`${API}/comparison/${sid}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        film_a: pair.a.film_uri,
        film_b: pair.b.film_uri,
        winner,
      }),
    });

    setCount((c) => c + 1);
    advance();
  }

  function skip() {
    if (!pair || pair.done) return;
    advance();
  }

  function exclude(film_uri) {
    if (!pair || pair.done) return;

    fetch(`${API}/exclude/${sid}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ film_uri }),
    });

    advance();
  }

  useEffect(() => {
    function onKey(e) {
      if (!pair || pair.done) return;
      if (e.key === "ArrowLeft") choose(pair.a.film_uri);
      if (e.key === "ArrowRight") choose(pair.b.film_uri);
      if (e.key === "s") skip();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (view === "results") return <Results sid={sid} onBack={() => setView("compare")} />;

    if (!sid) {
    return <Landing onSession={(id) => { localStorage.setItem(KEY, id); setSid(id); }} />;
  }

  if (!ready) {
    return (
      <Waiting
        sid={sid}
        onReady={() => setReady(true)}
        onReset={() => { localStorage.removeItem(KEY); setSid(null); }}
      />
    );
  }

  if (!pair) return <div className="stage">Loading your films…</div>;
  if (pair.done) return <div className="stage">You've compared everything.</div>;

  return (
    <div className="stage">
      <p className="question">
        Which would you rather experience for the first time again?
      </p>

      <div className="pair">
        <Poster
          film={pair.a}
          onPick={() => choose(pair.a.film_uri)}
          onExclude={() => exclude(pair.a.film_uri)}
        />
        <Poster
          film={pair.b}
          onPick={() => choose(pair.b.film_uri)}
          onExclude={() => exclude(pair.b.film_uri)}
        />
      </div>

      <div className="controls">
        <button className="quiet" onClick={skip}>Skip</button>
        <button className="quiet" onClick={() => setView("results")}>See results</button>
        <span className="progress">{count} compared</span>
      </div>
    </div>
  );
}

function Poster({ film, onPick, onExclude }) {
  return (
    <div className="slot">
      <button className="poster" onClick={onPick}>
        {film.poster ? (
          <img src={film.poster} alt="" />
        ) : (
          <span className="noposter">{film.name}</span>
        )}
        <span className="title">{film.name}</span>
        <span className="meta">{film.year}</span>
      </button>
      <button className="quiet small" onClick={onExclude}>Not a movie</button>
    </div>
  );
}