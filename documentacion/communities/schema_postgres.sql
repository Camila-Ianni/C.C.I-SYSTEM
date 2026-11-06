-- =============================================================================
-- C.C.I. SYSTEM — SUBSISTEMA CCI COMMUNITIES
-- Artefacto de Referencia DDL PostgreSQL 16 (Fase Futura / No Integrado en Runtime)
--
-- NOTA ARQUITECTÓNICA IMPORTANTE (Fase 0.2):
-- En esta entrega, SQLite 3 en modo WAL (`PRAGMA journal_mode=WAL`, `PRAGMA foreign_keys=ON`)
-- es el ÚNICO motor de base de datos activo y soportado en `backend/communities/repository.py`
-- y en `deploy/docker-compose.communities.yml` (`/data/cci_communities.sqlite3`).
-- Este archivo se conserva exclusivamente como especificación de referencia de fase futura
-- para una eventual migración horizontal a PostgreSQL 16 y NO está conectado al runtime actual.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------------------------
-- 1. IDENTIDAD Y CONFIGURACIONES DE USUARIO
-- -----------------------------------------------------------------------------
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(32) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(512),
    status VARCHAR(20) NOT NULL DEFAULT 'offline', -- online, idle, dnd, offline, invisible
    custom_status VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users (username);
CREATE INDEX idx_users_email ON users (email);

CREATE TABLE user_settings (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    audio_input_device VARCHAR(255),
    audio_output_device VARCHAR(255),
    output_volume NUMERIC(3,2) NOT NULL DEFAULT 1.0,
    input_sensitivity NUMERIC(3,2) NOT NULL DEFAULT 0.5,
    ptt_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ptt_hotkey VARCHAR(64),
    noise_suppression BOOLEAN NOT NULL DEFAULT TRUE,
    echo_cancellation BOOLEAN NOT NULL DEFAULT TRUE,
    privacy_preferences JSONB NOT NULL DEFAULT '{"allow_dms": true, "show_activity": true}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- 2. COMUNIDADES, ROLES Y MEMBRESÍAS
-- -----------------------------------------------------------------------------
CREATE TABLE communities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    name VARCHAR(64) NOT NULL,
    slug VARCHAR(64) UNIQUE NOT NULL,
    description TEXT,
    icon_url VARCHAR(512),
    banner_url VARCHAR(512),
    visibility VARCHAR(16) NOT NULL DEFAULT 'private', -- public, private
    max_members INT NOT NULL DEFAULT 500,
    max_streams_per_channel INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
);

CREATE INDEX idx_communities_owner ON communities (owner_id);
CREATE INDEX idx_communities_visibility ON communities (visibility) WHERE deleted_at IS NULL;

CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    community_id UUID NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    name VARCHAR(32) NOT NULL,
    color VARCHAR(7) NOT NULL DEFAULT '#99AAB5',
    position INT NOT NULL DEFAULT 0,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_community_role_name UNIQUE (community_id, name)
);

CREATE INDEX idx_roles_community ON roles (community_id, position);

CREATE TABLE permissions (
    id VARCHAR(64) PRIMARY KEY,
    category VARCHAR(32) NOT NULL,
    description TEXT NOT NULL
);

-- Catálogo canónico de permisos
INSERT INTO permissions (id, category, description) VALUES
    ('community.manage', 'community', 'Editar información, icono y ajustes de la comunidad'),
    ('community.view', 'community', 'Ver canales y contenido de la comunidad'),
    ('community.invites.create', 'community', 'Generar enlaces de invitación'),
    ('community.roles.manage', 'community', 'Crear, ordenar y asignar roles inferiores'),
    ('community.members.kick', 'moderation', 'Expulsar miembros de la comunidad'),
    ('community.members.ban', 'moderation', 'Prohibir permanentemente el acceso a miembros'),
    ('channels.manage', 'channels', 'Crear, editar y eliminar canales'),
    ('messages.read', 'chat', 'Leer historial y mensajes en canales de texto'),
    ('messages.send', 'chat', 'Enviar mensajes en canales de texto'),
    ('messages.manage', 'chat', 'Eliminar y fijar mensajes de otros miembros'),
    ('messages.attachments', 'chat', 'Subir imágenes y archivos adjuntos'),
    ('voice.connect', 'voice', 'Conectarse a salas de voz'),
    ('voice.speak', 'voice', 'Transmitir audio por micrófono'),
    ('voice.stream', 'voice', 'Transmitir pantalla, juego o cámara en vivo'),
    ('voice.mute_members', 'voice', 'Silenciar a otros participantes en la sala'),
    ('voice.move_members', 'voice', 'Mover o desconectar participantes de voz'),
    ('soundboard.play', 'soundboard', 'Reproducir sonidos en salas de voz'),
    ('soundboard.manage', 'soundboard', 'Subir y administrar sonidos de la comunidad')
ON CONFLICT (id) DO NOTHING;

CREATE TABLE role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id VARCHAR(64) NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    allowed BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE community_members (
    community_id UUID NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    nickname VARCHAR(32),
    status VARCHAR(16) NOT NULL DEFAULT 'active', -- active, muted, banned
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (community_id, user_id)
);

CREATE INDEX idx_members_user ON community_members (user_id);

CREATE TABLE member_roles (
    community_id UUID NOT NULL,
    user_id UUID NOT NULL,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (community_id, user_id, role_id),
    FOREIGN KEY (community_id, user_id) REFERENCES community_members(community_id, user_id) ON DELETE CASCADE
);

-- -----------------------------------------------------------------------------
-- 3. CANALES Y CONTROL DE ACCESO
-- -----------------------------------------------------------------------------
CREATE TABLE channel_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    community_id UUID NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    name VARCHAR(64) NOT NULL,
    position INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    community_id UUID NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    category_id UUID REFERENCES channel_categories(id) ON DELETE SET NULL,
    name VARCHAR(64) NOT NULL,
    type VARCHAR(16) NOT NULL, -- text, voice, stream
    topic TEXT,
    position INT NOT NULL DEFAULT 0,
    is_private BOOLEAN NOT NULL DEFAULT FALSE,
    max_participants INT NOT NULL DEFAULT 0, -- 0 = sin límite
    bitrate_kbps INT NOT NULL DEFAULT 64,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL,
    CONSTRAINT uq_community_channel_name UNIQUE (community_id, name)
);

CREATE INDEX idx_channels_community ON channels (community_id, position) WHERE deleted_at IS NULL;

CREATE TABLE channel_permission_overrides (
    channel_id UUID NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    target_type VARCHAR(16) NOT NULL, -- role, user
    target_id UUID NOT NULL,
    permission_id VARCHAR(64) NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    allow BOOLEAN NOT NULL DEFAULT FALSE,
    deny BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (channel_id, target_type, target_id, permission_id)
);

-- -----------------------------------------------------------------------------
-- 4. MENSAJERÍA, HISTORIAL Y ADJUNTOS
-- -----------------------------------------------------------------------------
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id UUID NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    content TEXT NOT NULL,
    reply_to_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    edited_at TIMESTAMPTZ NULL,
    deleted_at TIMESTAMPTZ NULL
);

CREATE INDEX idx_messages_channel_time ON messages (channel_id, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_messages_author ON messages (author_id);

CREATE TABLE message_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    storage_key VARCHAR(512) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(128) NOT NULL,
    size_bytes BIGINT NOT NULL,
    checksum_sha256 VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_attachments_message ON message_attachments (message_id);

-- -----------------------------------------------------------------------------
-- 5. MENSAJES PRIVADOS (PREPARADO PARA HABILITACIÓN)
-- -----------------------------------------------------------------------------
CREATE TABLE direct_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE direct_conversation_members (
    conversation_id UUID NOT NULL REFERENCES direct_conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (conversation_id, user_id)
);

CREATE TABLE direct_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES direct_conversations(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    edited_at TIMESTAMPTZ NULL,
    deleted_at TIMESTAMPTZ NULL
);

CREATE INDEX idx_dm_conversation_time ON direct_messages (conversation_id, created_at DESC) WHERE deleted_at IS NULL;

-- -----------------------------------------------------------------------------
-- 6. INVITACIONES
-- -----------------------------------------------------------------------------
CREATE TABLE invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    community_id UUID NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    inviter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code VARCHAR(32) UNIQUE NOT NULL,
    max_uses INT NOT NULL DEFAULT 0, -- 0 = ilimitado
    uses_count INT NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ NULL,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_invitations_code ON invitations (code) WHERE is_revoked IS FALSE;

-- -----------------------------------------------------------------------------
-- 7. SESIONES DE VOZ Y STREAMING (LIVEKIT COMPATIBLE)
-- -----------------------------------------------------------------------------
CREATE TABLE voice_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id UUID NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    livekit_room_name VARCHAR(128) NOT NULL,
    livekit_participant_id VARCHAR(128) NOT NULL,
    is_muted BOOLEAN NOT NULL DEFAULT FALSE,
    is_deafened BOOLEAN NOT NULL DEFAULT FALSE,
    is_screen_sharing BOOLEAN NOT NULL DEFAULT FALSE,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    left_at TIMESTAMPTZ NULL
);

CREATE INDEX idx_voice_sessions_channel ON voice_sessions (channel_id) WHERE left_at IS NULL;
CREATE INDEX idx_voice_sessions_user ON voice_sessions (user_id) WHERE left_at IS NULL;

-- -----------------------------------------------------------------------------
-- 8. SOUND DECK (BIBLIOTECAS DE SONIDO Y PERMISOS)
-- -----------------------------------------------------------------------------
CREATE TABLE sound_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope_type VARCHAR(16) NOT NULL, -- global, user, community
    scope_id UUID NULL,
    name VARCHAR(64) NOT NULL,
    position INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE sound_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID REFERENCES sound_categories(id) ON DELETE SET NULL,
    owner_type VARCHAR(16) NOT NULL, -- global, user, community
    owner_id UUID NULL,
    uploader_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    storage_key VARCHAR(512) NOT NULL,
    title VARCHAR(64) NOT NULL,
    duration_seconds NUMERIC(4,2) NOT NULL, -- máx 15.00s
    size_bytes BIGINT NOT NULL,             -- máx 5 MB
    format VARCHAR(10) NOT NULL DEFAULT 'mp3',
    volume_scale NUMERIC(3,2) NOT NULL DEFAULT 1.0,
    cooldown_seconds INT NOT NULL DEFAULT 5,
    checksum_sha256 VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sounds_owner ON sound_assets (owner_type, owner_id);

CREATE TABLE sound_permissions (
    sound_asset_id UUID NOT NULL REFERENCES sound_assets(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    can_play BOOLEAN NOT NULL DEFAULT TRUE,
    can_manage BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (sound_asset_id, role_id)
);

-- -----------------------------------------------------------------------------
-- 9. AUDITORÍA Y ACCIONES DE MODERACIÓN
-- -----------------------------------------------------------------------------
CREATE TABLE moderation_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    community_id UUID NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    actor_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    target_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    action VARCHAR(20) NOT NULL, -- warn, mute, kick, ban, unban
    reason TEXT,
    expires_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_moderation_community ON moderation_actions (community_id, created_at DESC);
CREATE INDEX idx_moderation_target ON moderation_actions (target_id);
