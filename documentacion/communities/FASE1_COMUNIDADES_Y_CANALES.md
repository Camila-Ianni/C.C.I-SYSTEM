# C.C.I. SYSTEM — CCI COMMUNITIES
## Fase 1: Comunidades, Roles, Miembros y Canales

**Fecha:** 2026-11-06  
**Subsistema:** CCI Communities  
**Estado:** IMPLEMENTACIÓN Y CERTIFICACIÓN APROBADA (Fase 1)  
**Rama:** `feature/communities-phase0-design`  

---

## 1. Alcance y Criterios de Aceptación Cumplidos

En cumplimiento de los criterios de aceptación de Fase 1 del documento de especificación:
- **"Dos cuentas independientes crean y administran comunidades; permisos negativos comprobados."**

### Funcionalidades Implementadas:
1. **Comunidades (CRUD y Ciclo de Vida)**:
   - Creación de comunidad con generación automática del rol `@everyone` (permisos base) y canales iniciales `#general` (texto) y `#General Voice` (voz).
   - Generación de slug único y saneado.
   - Visibilidad pública (descubrible) y privada (fail-closed, 403 para no miembros).
   - Edición de metadata (`name`, `description`, `icon_url`, `visibility`) protegida con permiso `community.manage`.
   - Transferencia segura de propiedad (`owner_id`) a miembros activos.
   - Eliminación lógica (`deleted_at`) restringida exclusivamente al propietario.
2. **Invitaciones y Gestión de Miembros**:
   - Creación de códigos de invitación únicos con control de cupos (`max_uses`) y expiración temporal en horas.
   - Incorporación a comunidades mediante consumo de invitación, respetando `max_members`.
   - Expulsión jerárquica de miembros (`community.members.kick`), prohibiendo expulsar a usuarios con rol superior o igual, y protegiendo de forma absoluta al propietario.
   - Abandono de comunidad (`leave`), impidiendo que el propietario abandone sin antes transferir la titularidad.
3. **Jerarquía de Roles y Permisos (Sección 5.2)**:
   - Creación de roles con nombre, color hexadecimal, bandera `is_admin`, permisos canónicos y posición numérica (`position`).
   - Restricción de jerarquía: ningún miembro puede crear o asignar roles con posición superior o igual a su propio rango.
   - Asignación y desasignación de roles a miembros (`member_roles`).
4. **Canales y Sobrescrituras de Acceso**:
   - Creación de canales de tipo `text`, `voice` y `stream` con tópicos y orden (`position`).
   - Canales privados invisibles e inaccesibles para miembros que no posean el permiso correspondiente.
   - Sobrescrituras explícitas (`channel_permission_overrides`) por rol o por usuario individual (`allow` / `deny`), habilitando visualización o lectura personalizada.
5. **Capa REST y Autenticación Central**:
   - Rutas montadas en `/api/v1/communities`, `/api/v1/invitations` y `/api/v1/channels`.
   - Todas las operaciones sensibles protegidas con `@require_auth` y derivación de identidad del token criptográfico.

---

## 2. Cobertura de Pruebas de Fase 1 ([`test_communities_phase1.py`](../../test_communities_phase1.py))

| # | Prueba Automatizada | Requisito Validado | Resultado |
| :--- | :--- | :--- | :--- |
| **01** | `test_01_community_creation_initializes_everyone_and_default_channels` | Creación de comunidad con `@everyone` y canales `#general` y `#General Voice` | **PASS** |
| **02** | `test_02_invitations_creation_expiration_and_join` | Invitaciones con límite de usos, expiración y rechazo tras agotarse | **PASS** |
| **03** | `test_03_private_community_access_control` | Rechazo 403 Forbidden para terceros ajenos en comunidades privadas | **PASS** |
| **04** | `test_04_public_community_discovery` | Listado y descubrimiento de comunidades públicas | **PASS** |
| **05** | `test_05_roles_hierarchy_and_permission_assignment` | Creación de rol Moderador, asignación y rechazo al intentar crear rol superior | **PASS** |
| **06** | `test_06_channel_privacy_and_permission_overrides` | Ocultamiento de canal privado y activación selectiva vía sobrescritura `allow` | **PASS** |
| **07** | `test_07_hierarchical_kick_and_protection_of_owner` | Expulsión de miembros por moderador y protección de 403 al intentar expulsar al dueño | **PASS** |
| **08** | `test_08_ownership_transfer_and_safe_leave` | Propietario no puede abandonar sin transferir; transferencia a Bob y salida exitosa | **PASS** |
| **09** | `test_09_community_deletion_by_owner_only` | Eliminación exclusiva por dueño y rechazo con 403 para terceros | **PASS** |
| **10** | `test_10_rest_api_negative_authorization_scenarios` | Rechazo 401 por falta de token, token inválido o token expirado | **PASS** |

---

## 3. Métricas del Runner Unificado ([`evaluations_report.json`](../../evaluations_report.json))

- **Suites Ejecutadas:** 14 de 14
- **Total de Pruebas:** 115
- **Aprobadas:** 115 (100%)
- **Fallidas:** 0
- **Errores:** 0
- **Tiempo de Ejecución:** 17.11 segundos
- **Regresiones en Consola PC:** 0 (1280x720, 60 FPS, 19 títulos verificados)
