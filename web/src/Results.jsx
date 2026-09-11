import { useEffect, useState } from "react";

import { API } from "./api";

const LABELS = { directors: "Directors", genres: "Genres", cast: "Actors" };

export default function Results({ sid, onBack }) {
  const [data, setData] = useState(null);
  const [dim, setDim] = useState(null);
  const [filter, setFilter] = useState(null);

  useEffect(() => {
    fetch(`${API}/results/${sid}`).then((r) => r.json()).then(setData);
  }, [sid]);

  if (!data) return <div className="stage">Working out your ranking…</div>;

  if (!data.ready) {
    return (
      <div className="stage">
        <p className="question">{data.needed} more comparisons to see results.</p>
        <button className="quiet" onClick={onBack}>Keep comparing</button>
      </div>
    );
  }

  function pickDim(key) {
    setDim(key);
    setFilter(null);
  }

  function pickEntry(key, entry) {
    setDim(key);
    setFilter(entry);
  }

    return (
    <div className="stage wide">
      <div className="topbar">
        <button className="quiet" onClick={onBack}>Keep comparing</button>
        <span className="progress">{data.count} compared</span>
      </div>

      <div className="filterbar">
        <button
          className={`chip ${!dim ? "on" : ""}`}
          onClick={() => pickDim(null)}
        >
          All films
        </button>
        {Object.entries(data.subcategories)
          .filter(([, sub]) => sub.unlocked)
          .map(([key]) => (
            <button
              key={key}
              className={`chip ${dim === key ? "on" : ""}`}
              onClick={() => pickDim(key)}
            >
              {LABELS[key]}
            </button>
          ))}
      </div>

      {dim && (
        <div className="filterbar values">
          {data.subcategories[dim].entries.map((e) => (
            <button
              key={e.name}
              className={`chip ${filter?.name === e.name ? "on" : ""}`}
              onClick={() => setFilter(e)}
            >
              {e.name}
            </button>
          ))}
        </div>
      )}

      <Grid films={filter ? filter.films : data.top_films} />

      <p className="note">Faded films need more comparisons.</p>

      <div className="subcats">
        {Object.entries(data.subcategories).map(([key, sub]) => (
          <div className="subcat" key={key}>
            <p className="section-label">{LABELS[key]}</p>
            {sub.unlocked ? (
              <>
                <p className="leaders">{sub.leaders.join(" and ")}</p>
                <ul className="entries">
                  {sub.entries.slice(0, 5).map((e) => (
                    <li key={e.name}>
                      <button className="link" onClick={() => pickEntry(key, e)}>
                        {e.name}
                      </button>
                      <span className="faint"> {e.n_films}</span>
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="locked">{sub.more_needed} more comparisons</p>
            )}
          </div>
        ))}
      </div>

      <p className="attribution">
        This product uses TMDB and the TMDB APIs but is not endorsed, certified,
        or otherwise approved by TMDB.
      </p>
    </div>
  );
}

function Grid({ films }) {
  return (
    <div className="grid">
      {films.map((f, i) => (
        <div className="cell" key={f.film_uri}>
          <div
            className="cell-img"
            style={{ opacity: 0.45 + 0.55 * Math.min(1, f.n_comparisons / 6) }}
          >
            {f.poster ? (
              <img src={f.poster} alt="" />
            ) : (
              <span className="noposter">{f.name}</span>
            )}
          </div>
          <span className="cell-score">{f.score.toFixed(1)}</span>
          <span className="cell-rank">{i + 1}</span>
        </div>
      ))}
    </div>
  );
}