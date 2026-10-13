-- Schéma PostgreSQL du projet. Idempotent : peut être rejoué sans risque.

-- Référentiel des valeurs : un ticker (symbole TradingView / Kaggle) par action.
CREATE TABLE IF NOT EXISTS instruments (
    ticker      TEXT PRIMARY KEY,
    name        TEXT,
    kind        TEXT NOT NULL DEFAULT 'stock',   -- stock | index
    sector      TEXT,
    bvc_name    TEXT UNIQUE,                     -- nom affiché sur casablanca-bourse.com
    in_masi20   BOOLEAN
);

-- Historique quotidien (Kaggle/TradingView), puis complété par la collecte.
CREATE TABLE IF NOT EXISTS prices_daily (
    ticker  TEXT NOT NULL,
    day     DATE NOT NULL,
    open    DOUBLE PRECISION,
    high    DOUBLE PRECISION,
    low     DOUBLE PRECISION,
    close   DOUBLE PRECISION NOT NULL,
    volume  DOUBLE PRECISION,
    source  TEXT NOT NULL,                       -- kaggle | live
    PRIMARY KEY (ticker, day)
);

-- Collecte quotidienne : une ligne par séance pour l'état du marché.
CREATE TABLE IF NOT EXISTS live_sessions (
    session_date        DATE PRIMARY KEY,
    market_status       TEXT,
    closed              BOOLEAN,
    masi                DOUBLE PRECISION,
    masi_var_pct        DOUBLE PRECISION,
    masi20              DOUBLE PRECISION,
    masi20_var_pct      DOUBLE PRECISION,
    capitalisation_mad  DOUBLE PRECISION,
    volume_global_mad   DOUBLE PRECISION,
    same_prices_as_previous BOOLEAN,
    fetched_at_utc      TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS live_quotes (
    session_date  DATE NOT NULL REFERENCES live_sessions ON DELETE CASCADE,
    bvc_name      TEXT NOT NULL,
    price         DOUBLE PRECISION,
    var_pct       DOUBLE PRECISION,
    PRIMARY KEY (session_date, bvc_name)
);

CREATE TABLE IF NOT EXISTS live_tops (
    session_date  DATE NOT NULL REFERENCES live_sessions ON DELETE CASCADE,
    kind          TEXT NOT NULL,                 -- volume | hausses | baisses
    rank          SMALLINT NOT NULL,
    bvc_name      TEXT NOT NULL,
    price         DOUBLE PRECISION,
    value         DOUBLE PRECISION,              -- volume en MAD ou variation en %
    PRIMARY KEY (session_date, kind, rank)
);

-- Publications des émetteurs (AMMC).
CREATE TABLE IF NOT EXISTS communiques (
    id            BIGSERIAL PRIMARY KEY,
    published_at  TIMESTAMPTZ NOT NULL,
    title         TEXT NOT NULL,
    issuer_raw    TEXT,
    subject       TEXT,
    pdf_url       TEXT,
    ticker        TEXT,                          -- rempli par la table d'alias
    event_type    TEXT,                          -- rempli par le classement
    UNIQUE (published_at, title)
);
CREATE INDEX IF NOT EXISTS communiques_ticker_idx ON communiques (ticker, published_at);

-- Statut de l'émetteur selon data/ref/emetteurs_alias.csv : cotee | sans_historique | non_cotee | plusieurs | inconnu.
ALTER TABLE communiques ADD COLUMN IF NOT EXISTS issuer_status TEXT;
CREATE INDEX IF NOT EXISTS communiques_type_idx ON communiques (event_type);

-- Sauts de prix au-delà de la limite de ±10 % par séance (voir bvcsurv.qualite).
CREATE TABLE IF NOT EXISTS price_flags (
    ticker    TEXT NOT NULL,
    day       DATE NOT NULL,
    kind      TEXT NOT NULL,                     -- rupture | aller_retour
    ratio     DOUBLE PRECISION NOT NULL,         -- cours / cours précédent
    sessions  INTEGER NOT NULL,                  -- séances du MASI depuis le cours précédent
    PRIMARY KEY (ticker, day)
);

-- Détail par valeur de la page /live-market/actions (symbole officiel = ticker).
CREATE TABLE IF NOT EXISTS live_stocks (
    session_date        DATE NOT NULL REFERENCES live_sessions ON DELETE CASCADE,
    ticker              TEXT NOT NULL,
    status              TEXT,                    -- T traité | NT non traité | S suspendu
    open                DOUBLE PRECISION,
    high                DOUBLE PRECISION,
    low                 DOUBLE PRECISION,
    last                DOUBLE PRECISION,
    reference           DOUBLE PRECISION,        -- cours de la veille
    var_pct             DOUBLE PRECISION,
    volume_mad          DOUBLE PRECISION,
    quantity            DOUBLE PRECISION,        -- titres échangés (même unité que le volume Kaggle)
    trades              INTEGER,
    capitalisation_mad  DOUBLE PRECISION,
    shares              DOUBLE PRECISION,
    PRIMARY KEY (session_date, ticker)
);
