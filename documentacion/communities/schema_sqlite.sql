-- =============================================================================
-- C.C.I. SYSTEM — SUBSISTEMA CCI COMMUNITIES
-- Esquema Físico Relacional Canónico SQLite 3 (Modo WAL)
--
-- MOTOR DE BASE DE DATOS OFICIAL Y SOPORTADO: SQLite 3 (WAL)
-- Implementado en runtime por `backend/communities/repository.py` sobre:
--   - Escritorio local: `.cci-user-data/cci_communities.sqlite3`
--   - Contenedor Docker (`api`): `/data/cci_communities.sqlite3`
-- =============================================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 10000;

CREATE TABLE IF NOT EXISTS communities (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    description TEXT,
    icon_url TEXT,
    banner_url TEXT,
    visibility TEXT NOT NULL DEFAULT 'private',
    max_members INTEGER NOT NULL DEFAULT 500,
    max_streams_per_channel INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    deleted_at REAL NULL
);

CREATE TABLE IF NOT EXISTS roles (
    id TEXT PRIMARY KEY,
    community_id TEXT NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT '#99AAB5',
    position INTEGER NOT NULL DEFAULT 0,
    is_default INTEGER NOT NULL DEFAULT 0,
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    UNIQUE (community_id, name)
);

CREATE TABLE IF NOT EXISTS permissions (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id TEXT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id TEXT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    allowed INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS community_members (
    community_id TEXT NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    nickname TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    joined_at REAL NOT NULL,
    PRIMARY KEY (community_id, user_id)
);

CREATE TABLE IF NOT EXISTS member_roles (
    community_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role_id TEXT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (community_id, user_id, role_id),
    FOREIGN KEY (community_id, user_id) REFERENCES community_members(community_id, user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS channel_categories (
    id TEXT PRIMARY KEY,
    community_id TEXT NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS channels (
    id TEXT PRIMARY KEY,
    community_id TEXT NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    category_id TEXT REFERENCES channel_categories(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    topic TEXT,
    position INTEGER NOT NULL DEFAULT 0,
    is_private INTEGER NOT NULL DEFAULT 0,
    max_participants INTEGER NOT NULL DEFAULT 0,
    bitrate_kbps INTEGER NOT NULL DEFAULT 64,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    deleted_at REAL NULL,
    UNIQUE (community_id, name)
);

CREATE TABLE IF NOT EXISTS channel_permission_overrides (
    channel_id TEXT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    permission_id TEXT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    allow INTEGER NOT NULL DEFAULT 0,
    deny INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (channel_id, target_type, target_id, permission_id)
);

CREATE TABLE IF NOT EXISTS invitations (
    id TEXT PRIMARY KEY,
    community_id TEXT NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    inviter_id TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    max_uses INTEGER NOT NULL DEFAULT 0,
    uses_count INTEGER NOT NULL DEFAULT 0,
    expires_at REAL NULL,
    is_revoked INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    author_id TEXT NOT NULL,
    content TEXT NOT NULL,
    reply_to_id TEXT REFERENCES messages(id) ON DELETE SET NULL,
    is_pinned INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    edited_at REAL NULL,
    deleted_at REAL NULL
);

CREATE TABLE IF NOT EXISTS message_attachments (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    storage_key TEXT NOT NULL,
    filename TEXT NOT NULL,
    content_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    checksum_sha256 TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS user_presence (
    user_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'offline',
    custom_status TEXT,
    last_seen REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS voice_sessions (
    id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    livekit_room_name TEXT NOT NULL,
    livekit_participant_id TEXT NOT NULL,
    is_muted INTEGER NOT NULL DEFAULT 0,
    is_deafened INTEGER NOT NULL DEFAULT 0,
    is_screen_sharing INTEGER NOT NULL DEFAULT 0,
    joined_at REAL NOT NULL,
    left_at REAL NULL
);

CREATE TABLE IF NOT EXISTS sound_categories (
    id TEXT PRIMARY KEY,
    scope_type TEXT NOT NULL,
    scope_id TEXT NULL,
    name TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sound_assets (
    id TEXT PRIMARY KEY,
    category_id TEXT REFERENCES sound_categories(id) ON DELETE SET NULL,
    owner_type TEXT NOT NULL,
    owner_id TEXT NULL,
    uploader_id TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    title TEXT NOT NULL,
    duration_seconds REAL NOT NULL DEFAULT 0.0,
    file_size_bytes INTEGER NOT NULL,
    format TEXT NOT NULL DEFAULT 'mp3',
    volume_scale REAL NOT NULL DEFAULT 1.0,
    cooldown_seconds INTEGER NOT NULL DEFAULT 5,
    checksum_sha256 TEXT NOT NULL,
    created_at REAL NOT NULL,
    deleted_at REAL NULL
);

CREATE TABLE IF NOT EXISTS sound_permissions (
    sound_asset_id TEXT NOT NULL REFERENCES sound_assets(id) ON DELETE CASCADE,
    role_id TEXT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    can_play INTEGER NOT NULL DEFAULT 1,
    can_manage INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (sound_asset_id, role_id)
);

CREATE TABLE IF NOT EXISTS user_sound_favorites (
    user_id TEXT NOT NULL,
    sound_id TEXT NOT NULL REFERENCES sound_assets(id) ON DELETE CASCADE,
    hotkey TEXT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY (user_id, sound_id)
);

CREATE TABLE IF NOT EXISTS sound_play_events (
    id TEXT PRIMARY KEY,
    sound_id TEXT NOT NULL REFERENCES sound_assets(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    played_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS stream_sessions (
    id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    stream_type TEXT NOT NULL DEFAULT 'screen',
    title TEXT NOT NULL,
    game_id TEXT NULL,
    resolution TEXT NOT NULL DEFAULT '1080p',
    fps INTEGER NOT NULL DEFAULT 60,
    bitrate_kbps INTEGER NOT NULL DEFAULT 4500,
    has_audio INTEGER NOT NULL DEFAULT 1,
    is_paused INTEGER NOT NULL DEFAULT 0,
    livekit_track_id TEXT NULL,
    started_at REAL NOT NULL,
    ended_at REAL NULL
);

CREATE TABLE IF NOT EXISTS moderation_actions (
    id TEXT PRIMARY KEY,
    community_id TEXT NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    actor_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT NULL,
    expires_at REAL NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    community_id TEXT NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    reporter_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    resolution_notes TEXT NULL,
    resolved_by TEXT NULL,
    created_at REAL NOT NULL,
    resolved_at REAL NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    community_id TEXT NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    actor_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    target_id TEXT NULL,
    details_json TEXT NULL,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_communities_owner ON communities(owner_id);
CREATE INDEX IF NOT EXISTS idx_channels_community ON channels(community_id, position);
CREATE INDEX IF NOT EXISTS idx_messages_channel_created ON messages(channel_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_members_user ON community_members(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_community_created ON audit_log(community_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_voice_sessions_channel ON voice_sessions(channel_id, left_at);
CREATE INDEX IF NOT EXISTS idx_stream_sessions_channel ON stream_sessions(channel_id, ended_at);
