# C.C.I. SYSTEM — FASE 2: AMIGOS, GRUPOS, ROLES Y PRESENCIA
**Versión del proyecto:** v2.1.0  
**Fecha de finalización:** 5 de noviembre de 2026  
**Rama activa:** `feature/evolution-phase2`  
**Autora:** Camila Carolina Ianni  

---

## 1. Resumen de Entregables de la Fase 2

La Fase 2 implementa el Módulo B (Amigos y Grupos) mediante lógica de negocio desacoplada en Python, persistencia relacional en SQLite y control de acceso basado en roles (RBAC).

| Módulo / Archivo | Responsabilidad Técnica |
|---|---|
| [backend/friends_service.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/backend/friends_service.py) | Servicio de amistades, presencia en tiempo real (online, away, busy, offline), juego activo, creación de grupos y jerarquía de permisos. |
| [cci_database.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/cci_database.py) | Métodos relacionales de persistencia en SQLite para `friendships`, `groups` y `group_members`. |
| [backend/server.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/backend/server.py) | Endpoints REST para solicitudes, bloqueos, presencia, gestión de grupos, expulsiones y transferencia de propiedad. |
| [test_phase2_evolution.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/test_phase2_evolution.py) | 11 pruebas unitarias e integración que validan el 100% de los flujos y restricciones. |

---

## 2. Reglas de Negocio y Control de Acceso (RBAC)

### 2.1 Amigos y Presencia
- **Solicitud de Amistad:** Estado `pending` inicial. Solo se convierte en amistad activa tras la aceptación del destinatario (`accepted`).
- **Prevención de Auto-solicitud:** Un usuario no puede enviarse una solicitud a sí mismo.
- **Bloqueos:** Los usuarios bloqueados no pueden emitir solicitudes ni ver presencia mutua.
- **Presencia en Tiempo Real:** Estados `online`, `away`, `busy`, `offline` con reporte del juego actual en ejecución (ej. "Da Vinci Fighters").
- **Privacidad:** La lista de amigos expone únicamente `friend_id`, estado de presencia y juego activo; no divulga datos privados (correos, hashes ni IPs).

### 2.2 Jerarquía y Permisos de Grupos
1. **Rol Owner (Propietario):**
   - Crea el grupo, asigna/modifica roles de miembros (`admin`, `member`), expulsa a cualquier integrante, transfiere la propiedad o elimina el grupo.
   - Si el dueño abandona el grupo, la propiedad se delega automáticamente al admin más antiguo o al miembro con mayor antigüedad.
2. **Rol Admin (Administrador):**
   - Invita nuevos integrantes y puede expulsar a usuarios con rol `member`.
   - **Restricción estricta:** Un admin **no puede** expulsar al dueño ni a otros administradores.
3. **Rol Member (Miembro):**
   - Participa del grupo y puede abandonarlo voluntariamente. No posee permisos de expulsión ni invitación en grupos privados.

---

## 3. Endpoints REST Implementados

- `POST /api/v1/friends/request`: Enviar solicitud de amistad.
- `POST /api/v1/friends/respond`: Aceptar o rechazar solicitud.
- `GET /api/v1/friends/<user_id>`: Listado de amigos con presencia y solicitudes pendientes.
- `POST /api/v1/presence`: Actualizar presencia (`status`, `current_game`).
- `POST /api/v1/groups/create`: Crear grupo (creador adquiere rol `owner`).
- `GET /api/v1/groups/<group_id>`: Obtener detalle del grupo y miembros.
- `POST /api/v1/groups/<group_id>/invite`: Invitar miembro (validado por RBAC).
- `POST /api/v1/groups/<group_id>/kick`: Expulsar miembro (validado por RBAC).
- `POST /api/v1/groups/<group_id>/leave`: Abandonar grupo con delegación de dueño.
- `POST /api/v1/groups/<group_id>/transfer`: Transferir propiedad a otro miembro.
- `POST /api/v1/groups/<group_id>/role`: Promover o degradar roles.

---

## 4. Resultados de Pruebas de Regresión y Nuevas Pruebas

```
Ran 36 tests in 1.893s
OK (100% de éxito en todas las suites acumuladas)
- test_phase1_evolution.py: 9 tests pasados
- test_phase2_evolution.py: 11 tests pasados
- test_phase2.py: 9 tests pasados
- test_phase3.py: 7 tests pasados
```
- Consola de escritorio [main.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/main.py) y catálogo de 19 juegos permanecen 100% estables e intactos.
