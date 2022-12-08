
create table if not exists application_tokens (
    id serial not null primary key,
    provider_name text not null unique,
    payload jsonb not null,
    issued_at timestamptz not null
);