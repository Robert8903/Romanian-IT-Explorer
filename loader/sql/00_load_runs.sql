-- One row per load attempt. Kept between runs: it is how a repeat knows what already finished.
CREATE TABLE IF NOT EXISTS load_runs (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fingerprint text NOT NULL,
    status      text NOT NULL,
    raw_copy_s  double precision,
    cleaning_s  double precision,
    index_s     double precision,
    finished_at timestamptz NOT NULL DEFAULT now()
);
