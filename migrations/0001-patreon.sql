create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated = now();
  return new;
END;
$$ LANGUAGE plpgsql;

create table if not exists wtf (
    id serial primary key,
    your_mom text not null
);
create table if not exists patreons (
    id serial primary key,
    created timestamptz not null default current_timestamp,
    updated timestamptz not null default current_timestamp,
    patreon_id bigint not null unique,
    active boolean
);

create table if not exists patreon_social_connections (
    patreon_id bigint not null,
    provider_name text not null,
    provider_id text not null,
    url text null default null,
    unique (patreon_id, provider_name)
);
create table if not exists patreon_tiers (
    patreon_id bigint references patreons (patreon_id),
    tier_id integer not null,
    unique (patreon_id, tier_id)
);
create index if not exists idx_patreon_social_connections_provider_name on patreon_social_connections (provider_name);
create index if not exists idx_patreon_social_connections_provider_id on patreon_social_connections (provider_id);
create trigger set_patreon_timestamp
        before update on patreons
        for each row
            execute procedure set_updated_at();
