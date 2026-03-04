# Software Architecture — Directed Evolution Portal

> **Developer reference.** For end-user guidance see [HELP_GUIDE.md](HELP_GUIDE.md).

---

## 1. System Overview

The Directed Evolution Portal is a three-tier web application.

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Browser (Client)                           │
│   Next.js 14 · TypeScript · Tailwind CSS · react-plotly.js         │
└───────────────────────────────┬─────────────────────────────────────┘
                                │  HTTP / JSON  (credentials: include)
                                │  PNG blobs  (violin plot)
                                │  HTML blobs (fingerprint iframe)
┌───────────────────────────────▼─────────────────────────────────────┐
│                       Flask API Server                              │
│   Python 3.13 · SQLAlchemy · Flask-Session · matplotlib · Plotly   │
│   Runs on http://localhost:8000                                     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │  psycopg3  (TLS)
┌───────────────────────────────▼─────────────────────────────────────┐
│                    Neon Serverless PostgreSQL                       │
│   Tables: users · experiments · variant_data · mutations            │
└─────────────────────────────────────────────────────────────────────┘

External APIs
  └─ UniProt REST API  →  protein sequence + feature annotations
```

---

## 2. Repository Layout

```
Directed-Evolution-Portal/
├── backend/                        Flask application
│   ├── run.py                      Entry point — creates and starts the Flask app
│   ├── config.py                   Config loaded from backend/.env
│   ├── database.py                 SQLAlchemy engine, scoped session, Base
│   ├── models/
│   │   ├── user.py                 User (bcrypt password, UUID PK)
│   │   └── experiment.py           Experiment, VariantData, Mutation
│   ├── routes/
│   │   ├── auth.py                 /api/auth  — register · login · logout · me
│   │   ├── experiments.py          /api/experiments  — CRUD + upload + analysis + plots
│   │   ├── uniprot.py              /api/uniprot  — proxy to UniProt REST
│   │   └── landscape.py            /api/landscape  — activity landscape embedding
│   ├── services/
│   │   ├── user_service.py         Auth business logic (bcrypt, session)
│   │   ├── experiment_service.py   Experiment CRUD
│   │   ├── experimental_data_parser.py  CSV/TSV upload → VariantData rows
│   │   ├── activity_calculator.py  Activity score normalisation
│   │   ├── plasmid_validation.py   ORF detection, codon-to-protein translation
│   │   ├── sequence_analyzer.py    Needleman-Wunsch alignment, mutation detection (stateless)
│   │   ├── sequence_tools.py       Codon tables, AA helpers
│   │   ├── fingerprint_plot.py     3-D residue heatmap (Biopython + PDB) → HTML blob
│   │   ├── landscape_service.py    UMAP / PCA embedding (lazy torch/ESM imports)
│   │   ├── uniprot_client.py       UniProt feature fetch with disk cache
│   │   └── errors.py               Typed error classes
│   └── requirements.txt
│
├── frontend/                       Next.js application (App Router)
│   ├── app/
│   │   ├── layout.tsx              Root layout — font, global CSS
│   │   ├── page.tsx                Landing / auth gate
│   │   └── dashboard/
│   │       ├── layout.tsx          Dashboard shell with sidebar nav
│   │       ├── page.tsx            Dashboard home
│   │       ├── experiments/        Experiment list + detail pages
│   │       ├── new-experiment/     Guided experiment creation wizard
│   │       └── analysis/
│   │           └── page.tsx        Analysis dashboard (tabs)
│   ├── components/
│   │   ├── analysis/
│   │   │   ├── activity-distribution-chart.tsx  Violin plot (PNG, max-h-[500px])
│   │   │   ├── top-performers-table.tsx          Top 10 variants table
│   │   │   ├── mutation-fingerprint.tsx           3-D residue heatmap (Plotly iframe)
│   │   │   └── activity-landscape.tsx             UMAP/PCA scatter (Plotly)
│   │   ├── dashboard-nav.tsx       Sidebar navigation
│   │   └── ui/                     shadcn/ui primitives
│   ├── hooks/                      Custom React hooks (useUser, etc.)
│   ├── lib/
│   │   ├── types.ts                Shared TypeScript interfaces
│   │   └── utils.ts                cn() and other helpers
│   ├── styles/
│   └── public/
│
├── package.json                    Root — `npm run dev` starts both servers concurrently
├── ARCHITECTURE.md                 This file
└── HELP_GUIDE.md                   End-user manual
```

---

## 3. Database Schema

```
users
  id            UUID  PK
  email         TEXT  UNIQUE
  password_hash TEXT
  created_at    TIMESTAMP

experiments
  id                  UUID  PK
  user_id             UUID  FK → users.id  (CASCADE DELETE)
  name                TEXT
  protein_accession   TEXT          ← UniProt accession
  wt_protein_sequence TEXT
  protein_features    JSONB         ← UniProt annotations
  plasmid_name        TEXT
  plasmid_sequence    TEXT
  validation_status   TEXT          ← pending | valid | invalid
  validation_data     JSONB
  analysis_status     TEXT          ← not_started | analyzing | completed | failed
  created_at / updated_at TIMESTAMP

variant_data
  id                           UUID  PK
  experiment_id                UUID  FK → experiments.id  (CASCADE DELETE)
  plasmid_variant_index        TEXT  ← original row identifier from CSV
  generation                   INTEGER
  sequence                     TEXT  ← nucleotide sequence of the variant
  activity_score               FLOAT
  normalised_activity_score    FLOAT
  qc_status                    TEXT  ← passed | failed
  qc_flags                     JSONB ← list of failure reasons
  analysis_data                JSONB ← position-level detail from NW alignment

mutations
  id                    UUID  PK
  variant_data_id       UUID  FK → variant_data.id  (CASCADE DELETE)
  experiment_id         UUID  FK → experiments.id
  position              INTEGER       ← 1-based AA position in WT
  aligned_position      INTEGER       ← position in NW alignment
  wild_type             TEXT          ← WT codon
  mutant                TEXT          ← variant codon
  wt_codon              TEXT
  mut_codon             TEXT
  wt_aa                 TEXT          ← single-letter WT amino acid
  mut_aa                TEXT          ← single-letter variant amino acid
  mutation_type         TEXT          ← synonymous | non-synonymous
  generation_introduced INTEGER
  is_accumulated        BOOLEAN
```

---

## 4. Backend Architecture

### 4.1 Request lifecycle

```
Flask request
  ↓
Blueprint router  (auth / experiments / uniprot / landscape)
  ↓
Route handler     authentication check via session.get('user_id')
  ↓
Service layer     pure Python, no Flask imports
  ↓
SQLAlchemy scoped_session  (thread-local for background threads, request-scoped for HTTP)
  ↓
Neon PostgreSQL
```

### 4.2 Sequence analysis pipeline (background thread)

Triggered by `POST /api/experiments/<id>/analyze-sequences`:

```
1.  Load plasmid_sequence + wt_protein_sequence from DB
2.  On WT plasmid: locate_gene_fast() → (wt_gene_dna, gene_start, gene_length, is_gene_rc)
      Returns 4-tuple.  If gene is on the reverse-complement strand, is_gene_rc=True and
      start coordinate maps back via  (2*L - dna_end) % L  (not dna_start % L).
3.  For each variant in experiment:
    a. locate_gene_fast() / locate_gene_sw() fallback
          Extract gene window; RC-flip if is_gene_rc; translate → variant protein.
    b. sequence_analyzer._estimate_rotation_offset()
          Anchored vote over 5-AA windows to correct circular-plasmid rotation.
    c. sequence_analyzer._needleman_wunsch()
          Global alignment (match=1, mismatch=-1, gap=-2).
    d. sequence_analyzer.identify_mutations()
          Diff aligned sequences → list of {position, aligned_position,
          wt_aa, mut_aa, wt_codon, mut_codon, mutation_type, aa_change}.
    NOTE: SequenceAnalyzer is stateless — no instance attributes; all state is
          local to analyze_variant_batch() to prevent cross-request race conditions.
4.  Compute-first, write-second atomic transaction:
    DELETE FROM mutations WHERE experiment_id = <id>
    INSERT  all new Mutation rows
    COMMIT
5.  Update experiment.analysis_status = 'completed'
6.  db.remove()  — release scoped session for this thread
```

### 4.3 Plot generation (server-side)

**Violin plot** — `GET /api/experiments/<id>/plots/activity-distribution`

```
DB query → pandas DataFrame → matplotlib violin + whisker drawing
  figsize=(11,6), dpi=140, tight_layout
→ BytesIO buffer → send_file(buf, mimetype='image/png')
Frontend: fetch() → blob URL → <img max-h-[500px] object-contain>
```

**Mutation fingerprint** — `GET /api/experiments/<id>/plots/mutation-fingerprint?format=html`

```
DB query → residue × generation score matrix
→ Plotly 3-D surface figure → fig.to_html(full_html=True, include_plotlyjs='cdn')
→ send_file(buf, mimetype='text/html')
Frontend: <iframe key={url} src={backendUrl?format=html}>
  (CDN Plotly loads inside iframe — avoids Next.js bundle conflict)
```

---

## 5. Frontend Architecture

### 5.1 Routing

```
/                          Landing page / auth gate
/dashboard                 Summary stats
/dashboard/experiments     Experiment list
/dashboard/experiments/<id> Experiment detail + data upload
/dashboard/new-experiment  Guided creation wizard
/dashboard/analysis        Analysis dashboard
```

### 5.2 Data flow (Experiment detail page)

```
dashboard/experiments/[id]/page.tsx
  │
  ├─ loadExperiment()  — GET /api/experiments/<id>?include_variants=false
  │    Fast metadata-only fetch: clears full-page spinner immediately.
  │    Sets experiment name, status, analysis_status.
  │
  ├─ loadVariants()    — GET /api/experiments/<id>  (full, with variants)
  │    Slower fetch running in parallel; populates variant-dependent UI.
  │
  ├─ Global banners (rendered ABOVE <Tabs>, visible from any tab)
  │    Blue  — while analysisStatus === "analyzing" (shows elapsed seconds)
  │    Green — on analysis completion (dismissible, set via analysisBanner state)
  │
  ├─ Polling loop (5-second interval while analyzing)
  │    GET /api/experiments/<id>/analysis-status
  │    On "completed" → sets analysisBanner → calls loadVariants()
  │
  └─ Tabs
       ├─ overview     → <ActivityDistributionChart>  (fetches PNG from backend)
       │                 <TopPerformersTable>
       ├─ mutations    → <MutationFingerprint>        (Plotly iframe)
       └─ landscape    → <ActivityLandscape>          (Plotly scatter, UMAP/PCA)
```

### 5.3 Code splitting strategy

All four analysis components are loaded with `next/dynamic` + `ssr: false` to
keep `react-plotly.js` (~3 MB) out of the initial page bundle:

```typescript
const ActivityDistributionChart = dynamic(
  () => import("@/components/analysis/activity-distribution-chart")
        .then(m => ({ default: m.ActivityDistributionChart })),
  { ssr: false, loading: () => <Skeleton /> }
)
```

---

## 6. Authentication

- **Registration / Login**: `bcrypt` password hashing, credentials stored in `users` table.
- **Sessions**: Flask-Session with filesystem backend; session cookie sent on every request with `credentials: "include"`.
- **Auth check**: every protected route calls `session.get('user_id')`; returns 401 if absent.
- **No JWT**: sessions are server-side only; no token refresh logic required.

---

## 7. Key Design Decisions

| Decision                                              | Rationale                                                                                                                              |
| ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Flask over FastAPI                                    | Team familiarity; SQLAlchemy integration simpler                                                                                       |
| Scoped session (`db.remove()` in finally)             | Required when SQLAlchemy scoped_session is used in background daemon threads — prevents session leaks                                  |
| Compute-first, write-second for mutation analysis     | Prevents DB being left with an empty mutations table if the server restarts mid-analysis                                               |
| Server-side matplotlib PNG for violin plot            | Faithful replication of the original `activity_score_per_gen.py` without re-implementing KDE in JS                                    |
| Fingerprint plot streamed as full HTML (iframe)       | CDN Plotly loads freely inside `<iframe>`; avoids the bundle-version conflict that crashes `react-plotly.js` in Next.js App Router     |
| RC strand coordinate fix: `(2*L - dna_end) % L`      | `dna_start % L` is meaningless for reverse-complement coordinates; correct formula maps the RC endpoint back to plus-strand space      |
| Stateless `SequenceAnalyzer`                          | Removed `__init__` and all instance attributes so concurrent analyses cannot overwrite each other's gene state                         |
| Split `loadExperiment()` / `loadVariants()`           | Metadata-only fetch returns in ~200 ms, clearing the full-page spinner; variant data loads lazily without blocking navigation          |
| Global analysis banners above `<Tabs>`                | Banners placed outside the tab panel are visible regardless of which tab is active, so "analysis complete" is never hidden             |
| `extra_metadata` JSONB column on `variant_data`       | Preserves arbitrary extra columns from the upload TSV without schema changes                                                           |
| Positional fallback restricted to required fields     | Prevents the first non-required extra column from being silently consumed as `parent_plasmid_variant` during column mapping            |
| NaN/Inf sanitisation before JSONB serialise           | `numpy.nan` is not JSON-serialisable; sanitise loop converts to `None` to prevent 500 errors on metadata storage                      |
| Lazy imports in `landscape_service.py`                | `torch`, `esm`, `umap` are optional heavy dependencies; service degrades gracefully to one-hot encoding if unavailable                 |
| Needleman-Wunsch alignment in `sequence_analyzer`     | WT and variant sequences can differ in length due to indels; simple positional diff would mis-call all downstream residues             |
| Rotation offset estimation                            | Plasmid sequences are circular; PCR can amplify a differently-rotated read, shifting every position by a fixed offset                  |
| `dynamic()` imports on analysis page                  | Reduces initial Next.js compile from ~20 s to ~3 s by splitting Plotly out of the main bundle                                         |

---

## 8. Environment Variables

### backend/.env

| Variable       | Description                                                    |
| -------------- | -------------------------------------------------------------- |
| `SECRET_KEY`   | Flask session signing key                                      |
| `DATABASE_URL` | Neon PostgreSQL connection string (include `?sslmode=require`) |
| `FRONTEND_URL` | Allowed CORS origin (default `http://localhost:3000`)          |

### frontend/.env.local

| Variable                  | Description                                          |
| ------------------------- | ---------------------------------------------------- |
| `NEXT_PUBLIC_BACKEND_URL` | Flask API base URL (default `http://localhost:8000`) |

---

## 9. Development Setup

```bash
# 1. Clone
git clone <repo-url>
cd Directed-Evolution-Portal

# 2. Backend
cd backend
python -m venv .venv
# Windows:   .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in SECRET_KEY and DATABASE_URL

# 3. Frontend
cd ../frontend
pnpm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_BACKEND_URL

# 4. Run both servers from the root
cd ..
npm install
npm run dev
# → Flask on http://localhost:8000
# → Next.js on http://localhost:3000
```

---

## 10. Dependencies Summary

### Backend (Python)

| Package         | Purpose                                          |
| --------------- | ------------------------------------------------ |
| Flask 3.0       | HTTP framework                                   |
| SQLAlchemy ≥2.0 | ORM + scoped session                             |
| psycopg3        | PostgreSQL driver                                |
| Flask-Session   | Server-side session storage                      |
| Flask-CORS      | CORS headers                                     |
| bcrypt          | Password hashing                                 |
| numpy           | Numerical operations (alignment, stats)          |
| pandas          | DataFrame for plot data                          |
| matplotlib ≥3.8 | Server-side violin plot generation               |
| seaborn ≥0.13   | (available; activity_score_distribution_plot.py) |
| scipy           | Statistical functions                            |
| scikit-learn    | PCA fallback in landscape service                |
| requests        | UniProt API client                               |
| plotly          | (optional, landscape Plotly JSON)                |

### Frontend (Node)

| Package              | Purpose                                     |
| -------------------- | ------------------------------------------- |
| Next.js 14           | React framework (App Router)                |
| TypeScript           | Type safety                                 |
| Tailwind CSS         | Utility styling                             |
| shadcn/ui + Radix UI | Accessible component primitives             |
| react-plotly.js      | Interactive charts (fingerprint, landscape) |
| next-themes          | Dark mode                                   |
| pnpm                 | Package manager                             |
