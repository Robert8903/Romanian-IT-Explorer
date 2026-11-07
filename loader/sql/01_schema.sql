-- Staging tables hold the files as they are: everything is text, cleaning comes later.
DROP TABLE IF EXISTS staging_firms, staging_statuses, staging_status_codes, staging_accounts;

CREATE TABLE staging_firms (
    denumire text,
    cui text,
    cod_inmatriculare text,
    data_inmatriculare text,
    forma_juridica text,
    adr_judet text,
    adr_localitate text
);

CREATE TABLE staging_statuses (
    cod_inmatriculare text,
    cod text
);

CREATE TABLE staging_status_codes (
    cod text,
    denumire text
);

CREATE TABLE staging_accounts (
    year text,
    filing_format text,
    cui text,
    caen text,
    i1 text,
    i2 text,
    i3 text,
    i4 text,
    i5 text,
    i6 text,
    i7 text,
    i8 text,
    i9 text,
    i10 text,
    i11 text,
    i12 text,
    i13 text,
    i14 text,
    i15 text,
    i16 text,
    i17 text,
    i18 text,
    i19 text,
    i20 text
);

-- The statuses file also covers individuals, so it lands here first and only
-- the rows of companies we kept move on. This table disappears at commit.
CREATE TEMP TABLE all_statuses (LIKE staging_statuses) ON COMMIT DROP;
