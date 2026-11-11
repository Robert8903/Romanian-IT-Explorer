-- The optional indexes, in one place so they can be measured with and without.
CREATE INDEX company_profile_county_idx ON company_profile (county);
CREATE INDEX company_profile_status_group_idx ON company_profile (status_group);
CREATE INDEX company_profile_category_idx ON company_profile (category);
CREATE INDEX company_profile_employees_idx ON company_profile (employees DESC NULLS LAST);
CREATE INDEX financials_caen_idx ON financials (caen);
