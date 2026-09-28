-- Local seed data. The "Acme Talent" sample workspace is added in FND-014.

-- The API's database role (FND-003). Local-only password; hosted environments set their own
-- (docs/architecture/DEPLOYMENT.md). The seed never runs against hosted projects.
alter role fasthyr_api with login password 'fasthyr_api_local';
