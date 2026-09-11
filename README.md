# rankmymovies

**[rankmymovies.vercel.app](https://rankmymovies.vercel.app)**

Upload a Letterboxd export, answer head-to-heads, and get a ranking built from your choices instead of your previous ratings.
<img width="570" height="496" alt="Screenshot 2026-09-11 at 3 08 17 PM" src="https://github.com/user-attachments/assets/63e0b302-13c0-49e6-afdd-d17d3283cbf0" />

---
**As a longtime fan of Letterboxd, my biggest critique has always been that there's no way for me to rate movies that bring back fond childhood nostalgia using
the same scale as Oscar-worthy blockbusters.

So I built something different: rankmymovies. **

## The question

> **Which would you rather experience for the first time again?**

The chosen wording is comparative, concrete, and non-evaluative. It has a known bias — it favors films with front-loaded first viewings, so twists beat slow burns — and that's documented rather than hidden.

## How it works

**Ingest.** Letterboxd's API is request-only and explicitly not granted for data-analysis or recommendation projects, so the app reads the user-exported ZIP instead. `watched.csv` is the spine; ratings, likes, and declared favorites join onto it.

**Enrich.** Films carry no TMDB IDs, only name + year and a `boxd.it` link. A matching cascade resolves them: exact-year search first, then ±1 year and unfiltered search — but every looser tier requires an exact title match *and* a release date within three years.

**Pool.** Comparisons happen within a candidate pool of ~125–175 films, sized as `min(library, 175, max(60, 0.4 × library))`. This decouples comparison count from library size: a 300-film user and a 3,000-film user do the same number of head-to-heads and get comparable confidence.

**Rank.** Bradley-Terry with Gaussian priors. Each film's prior mean is the z-score of its rating within the user's own distribution; unrated films sit at the user's mean with wide variance, boosted +0.5 SD if hearted and +1.0 SD if a declared favorite. A rating always supersedes a boost.

Pair selection scores candidates on uncertainty × closeness × relevance, so comparisons concentrate where the model is unsure, the outcome is genuinely uncertain, and the result matters.

**Aggregate.** Film strengths roll up into directors, genres, and actors with evidence-weighted shrinkage toward the global mean. Genres additionally carry an inverse-frequency weight, so the ranking reports what's *distinctive* about a user's taste rather than that they, like everyone, watch a lot of drama.

**Gate.** A subcategory unlocks only when its leader separates from the field by a set multiple of its own uncertainty. When the top entries are statistically tied, they're reported as a tied group rather than forced into an order. Locked categories show a derived estimate — "actors: 122 more comparisons" — computed from real uncertainty rather than a round number.

## What was measured

**TMDB match rate: 316/320 (98.8%).** All four failures are TV series, correctly excluded from a film ranker. The real film match rate is 100%.

The naive cascade scored 318/320 — but inspecting the fuzzy-match tier showed two of those were wrong: *The Queen's Gambit* had matched a making-of documentary, *Hawkeye* likewise. Tightening the title constraint caught both and exposed a third, *Hawkeye* matching a 1988 martial-arts film with an identical title. A release-date window fixed that.

**A lower number with zero false positives beat a higher number with three.**

**Held-out validation.** The user's four declared Favorite Films were never given to the ranking model. Three of the four landed in the top 12.

## What was wrong first

**The second axis died on real data.** The original design had two dimensions: attachment from comparisons, rewatchability from diary rewatch flags. The test export contained **one** rewatch flag across 72 diary entries, and the diary covered only 22% of the library. The feature was cut before it was built.

**The pair selector spent its budget in the wrong place.** After the first 40 comparisons, the entire top 10 still had zero comparisons — every answer had gone to unrated and mid-tier films, because they carried the widest priors and the selector was maximizing uncertainty alone. Caught by reading the comparison counts rather than trusting the ranking. Adding a relevance term fixed it.

**Percentile scoring couldn't produce a meaningful 10.** Pure percentile mapping is positional, so the top film scores the same whether it's dominant or in a dead heat — six films cleared the perfect-10 threshold by arithmetic. The scale now uses percentiles for shape and the actual strength gap for the top, so a 10 has to be earned against the user's own best. Most sessions correctly return *no perfect 10s — yet*.

**Flat files didn't survive deployment.** Sessions and comparison logs were CSVs on disk; Render's filesystem is ephemeral, so a restart mid-session would have erased someone's 150 comparisons. Moved to Postgres. The append-only log design made the migration contained — the model and frontend didn't change.

## Design decisions worth naming

**Star ratings never constrain the outcome.** They inform which films get compared to each other, but any film can move anywhere. Tier-locking would have made the ranking look sensible immediately while guaranteeing it could never discover that a 3-star film is a top-5 favorite — which is the entire point.

**Every user gets the same model.** Features that only work for users whose data happens to contain the right signal were rejected, including one that would have worked well for the test library.

**Exclusions are manual, not automatic.** Music videos and filmed stage productions can be removed by the user rather than filtered by a runtime threshold, because where that line falls is a judgment, not a fact.

**Confidence is visible.** Films with few comparisons render faded in the results grid and sharpen as evidence accumulates, so "not placed yet" needs no explanation.

## Stack

FastAPI · Postgres · SQLAlchemy · pandas · NumPy · SciPy · React · Vite
Backend on Render, frontend on Vercel.

```
ingest.py      export CSVs → one film table with provenance flags
tmdb.py        matching cascade against TMDB
enrich.py      metadata fetch + global film cache
pool.py        candidate pool selection
compare.py     pair scoring and selection
model.py       Bradley-Terry fit with Gaussian priors
aggregate.py   shrinkage, IDF weighting, confidence gates
score.py       10-point scale
app.py         API
```

## Known limitations

- Sessions never expire; there's no cleanup job.
- The TMDB metadata cache is still file-backed, so it's wiped on each deploy. TMDB's terms also require a six-month cache expiry, which isn't yet enforced.
- `MIN_FILMS` thresholds were tuned against one library and won't scale to very large ones — they should be a fraction of pool size rather than a raw count.
- Actors whose filmographies overlap completely (e.g. two leads of the same five-film franchise) are mathematically indistinguishable and currently appear as separate entries.
- Render's free tier cold-starts at roughly 30 seconds.
- Enrichment takes 60–180 seconds on first upload depending on cache warmth.

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
createdb rankmymovies
cp .env.example .env          # add TMDB_API_KEY and DATABASE_URL
uvicorn app:app --reload

cd web && npm install && npm run dev
```

---

This product uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB.
