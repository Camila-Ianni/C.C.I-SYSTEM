# Original User Request

## 2026-10-09T20:51:10Z

# Teamwork Project: Metal Slug 1 Mission 1 Arcade Fidelity Overhaul

Requested team: Full multi-agent team (gameplay engineers, physics/level designers, retro audio/graphics specialists)

Fix all gameplay bugs, physics terrain inconsistencies, entity crashes, vehicle controls, HUD issues, and boss graphics to turn the Metal Slug 1 Mission 1 clone into an exact 1:1 arcade-accurate replica matching the reference gameplay.

Working directory: /Users/cami/Desktop/METAL SLUG
Integrity mode: development

## Requirements

### R1. Core Physics & Level Collision Fixes
- Reconstruct the terrain collision map across all 5 zones of Mission 1 (Beach x=0..565, Submarine x=565..1350, River Village x=1350..2200, Valley Path x=2200..3300, Boss Arena x=3300..4153).
- Remove artificial floating platforms over water; ensure the riverbed allows walking in shallow water and jumping on stilt watchtowers/huts.
- Ensure camera bounds and screen edges prevent player and vehicle fall-through or clipping.

### R2. Super Vehicle-001 (Metal Slug Tank) Bugfixes & Mechanics
- Fix the game-breaking crash in `MetalSlug` when activating Metal Slug Attack / Kamikaze (`AttributeError: 'MetalSlug' object has no attribute 'x'`).
- Ensure the player sprite hides properly when boarded inside the tank, and the pilot exit ("Slug Out") ejects the player cleanly with invincibility frames.
- Update the tank driving, jumping, suspension squash, and twin vulcan cannon aim (horizontal, diagonal, vertical) to authentic 360-degree rotation.
- Match HUD in tank mode: display `CANNON [ammo]` instead of `BOMB [ammo]`, and tank armor bar under player score.

### R3. Mission 1 Boss (Tetsuyuki) Visual & Combat Overhaul
- Fix sprite rendering in `TetsuyukiBoss`: remove the rectangular background cutout with white boxes, replacing it with the authentic multi-part animated sprites (cockpit, nose cannon, plasma turret, exhaust flames).
- Remove the non-arcade "BOSS: TETSUYUKI" yellow health bar from the HUD (original Neo-Geo arcade has no boss health bar).
- Implement the authentic 2-phase attack patterns: Phase 1 nose artillery cannon and deck gunners; Phase 2 roof hatch opening with plasma orb battery.
- Implement cascading boss explosion sequence and clean transition to Mission 1 Complete.

### R4. HUD, Timer & Arcade Presentation
- Fix stage timer: when timer reaches 00, trigger time-out death sequence instead of freezing at 00.
- Render authentic rescued POW badge counters in bottom-left corner (`LEVEL-4`, `CREDITS 09`, `1UP=X`).
- Ensure soldiers, vehicles, and items have proper chroma-key transparency without white bounding boxes.

## Acceptance Criteria

### Automated & Headless Verification
- [ ] Headless simulation runs 2000 continuous frames through all Mission 1 zones with 0 crashes, 0 unhandled exceptions, and 0 `AttributeError`s.
- [ ] Metal Slug tank boarding, driving, firing vulcan/cannon, and Metal Slug Attack execute without error.
- [ ] Timer reaching 00 correctly triggers player life loss.

### Visual & Behavioral Authenticity
- [ ] Boss arena displays clean waterfall backdrop with no white square borders or visual artifacting.
- [ ] Vehicle and player terrain navigation remains grounded at natural visual heights without floating over river water.
- [ ] No non-arcade HUD elements (e.g. boss health bar) are drawn on screen.
