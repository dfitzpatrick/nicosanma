
create table if not exists discord_persistent_views (
    id serial primary key,
    created timestamptz not null default current_timestamp,
    updated timestamptz not null default current_timestamp,
    designation text not null,
    guild_id bigint not null,
    channel_id bigint not null,
    message_id bigint not null unique,
    view_payload jsonb not null
);
create index if not exists idx_persistent_view_guild on discord_persistent_views (guild_id);
create index if not exists idx_persistent_view_channel on discord_persistent_views (channel_id);

create trigger set_persistent_timestamp
        before update on discord_persistent_views
        for each row
            execute procedure set_updated_at();
