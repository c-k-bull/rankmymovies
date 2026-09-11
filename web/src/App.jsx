import { useEffect, useState, useCallback } from "react";
import { API } from "./api";
import Landing from "./Landing";
import Waiting from "./Waiting";
import Results from "./Results";

const KEY = "rmm.session";
const QUEUE_TARGET = 3;

export default function App() {
  const [sid, setSid] = useState(() => localStorage.getItem(KEY));
  const [ready, setReady] = useState(false);
  const [queue, setQueue] = useState([]);
  const [count, setCount] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [view, setView] = useState("compare");

  const fetchPair = useCallback(async () => {
    const r = await fetch(`${API}/pair/${sid}`);
    return r.json();
  }, [sid]);

  const topUp = useCallback(() => {
    setQueue((q) => {
      if (q.length >= QUEUE_TARGET) return q;
      for (let i = 0; i < QUEUE_TARGET - q.length; i++) {
        fetchPair().then((p) => {
          setQueue((cur) => {
            if (p.done) return cur;
            const key = p.a.film_uri + p.b.film_uri;
            const dupe = cur.some((x) => x.a.film_uri + x.b.film_uri === key);
            return dupe || cur.length >= QUEUE_TARGET ? cur : [...cur, p];
          });
        });
      }
      return q;
    });
  }, [fetchPair]);

  useEffect(() => {
    if (!sid || !ready || loaded) return;
    setLoaded(true);
    fetchPair().then((first) => {
      setCount(first.count);
      if (!first.done) setQueue([first]);
      topUp();
    });
  }, [sid, ready, loaded, fetchPair, topUp]);

  const pair = queue[0] || null;

  useEffect(() => {
    queue.slice(1).forEach((p) => {
      [p.a, p.b].forEach((f) => {
        if (f.poster) new Image().src = f.poster;
      });
    });
  }, [queue]);

  function advance() {
    setQueue((q) => q.slice(1));
    topUp();
  }

  function choose(winner) {
    if (!pair) return;
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
    if (!pair) return;
    advance();
  }

  function exclude(film_uri) {
    if (!pair) return;
    fetch(`${API}/exclude/${sid}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ film_uri }),
    });
    advance();
  }

  useEffect(() => {
    function onKey(e) {
      if (!pair) return;
      if (e.key === "ArrowLeft") choose(pair.a.film_uri);
      if (e.key === "ArrowRight") choose(pair.b.film_uri);
      if (e.key === "s") skip();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (!sid) {
    return (
      <Landing
        onSession={(id) => {
          localStorage.setItem(KEY, id);
          setSid(id);
        }}
      />
    );
  }

  if (!ready) {
    return (
      <Waiting
        sid={sid}
        onReady={() => setReady(true)}
        onReset={() => {
          localStorage.removeItem(KEY);
          setSid(null);
        }}
      />
    );
  }

  if (view === "results") {
    return <Results sid={sid} onBack={() => setView("compare")} />;
  }

  if (!pair) return <div className="stage">Loading your films…</div>;

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