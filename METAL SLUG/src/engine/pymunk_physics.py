"""
Pymunk 2D Physics Engine Integration for Metal Slug.
Provides:
- Rigid body simulation for explosive barrels, bouncing crates, and artillery shells.
- Terrain collision representation using pymunk.Segment.
- Sub-pixel line-of-sight raycasting for AI detection and bullet trajectory calculations.
"""
import pymunk
import pygame

class PymunkPhysicsWorld:
    """Manages a Pymunk 2D simulation space aligned with the Metal Slug world coordinates."""
    
    # Collision categories / types
    COLLISION_TERRAIN = 1
    COLLISION_PLAYER = 2
    COLLISION_ENEMY = 3
    COLLISION_PROJECTILE = 4
    COLLISION_DEBRIS = 5
    COLLISION_PROP = 6

    def __init__(self, gravity=(0, 900)):
        self.space = pymunk.Space()
        self.space.gravity = gravity
        self.platforms = []
        self.debris_bodies = []

    def set_gravity(self, gx, gy):
        self.space.gravity = (gx, gy)

    def add_platform(self, platform):
        """Converts an arcade Platform into a static Pymunk Segment shape."""
        # Static body for scenery / ground
        body = self.space.static_body
        segment = pymunk.Segment(body, (platform.x1, platform.y1), (platform.x2, platform.y2), radius=1.0)
        segment.friction = 0.8
        segment.elasticity = 0.1
        segment.collision_type = self.COLLISION_TERRAIN
        
        # Sensor for semi-solid platforms if pass-through is needed
        if getattr(platform, 'semi_solid', False):
            segment.filter = pymunk.ShapeFilter(categories=self.COLLISION_TERRAIN)
            
        self.space.add(segment)
        self.platforms.append(segment)
        return segment

    def add_rigid_box(self, x, y, width, height, mass=15.0, friction=0.7, elasticity=0.2):
        """Adds a dynamic rigid-body box (e.g., tumbling wooden crates or explosive barrels)."""
        moment = pymunk.moment_for_box(mass, (width, height))
        body = pymunk.Body(mass, moment)
        body.position = (x, y)
        shape = pymunk.Poly.create_box(body, (width, height))
        shape.friction = friction
        shape.elasticity = elasticity
        shape.collision_type = self.COLLISION_PROP
        self.space.add(body, shape)
        return body, shape

    def add_bouncing_debris(self, x, y, vx, vy, radius=3.0, mass=1.0, elasticity=0.6):
        """Spawns an elastic physics particle (e.g. shrapnel, rock chunks, bullet shells)."""
        moment = pymunk.moment_for_circle(mass, 0, radius)
        body = pymunk.Body(mass, moment)
        body.position = (x, y)
        body.velocity = (vx, vy)
        shape = pymunk.Circle(body, radius)
        shape.friction = 0.5
        shape.elasticity = elasticity
        shape.collision_type = self.COLLISION_DEBRIS
        self.space.add(body, shape)
        self.debris_bodies.append((body, shape))
        return body, shape

    def raycast(self, start_pos, end_pos):
        """
        Performs a raycast segment query between start_pos and end_pos.
        Returns the first hit obstacle info or None if unobstructed line-of-sight.
        """
        query = self.space.segment_query_first(start_pos, end_pos, 1.0, pymunk.ShapeFilter())
        if query and query.shape:
            return {
                "point": query.point,
                "normal": query.normal,
                "alpha": query.alpha,
                "shape": query.shape
            }
        return None

    def step(self, dt=1.0 / 60.0):
        """Advances the physics simulation space by dt seconds."""
        self.space.step(dt)

    def clear(self):
        """Clears all dynamic and static shapes from the space."""
        for shape in list(self.space.shapes):
            self.space.remove(shape)
        for body in list(self.space.bodies):
            if body != self.space.static_body:
                self.space.remove(body)
        self.platforms.clear()
        self.debris_bodies.clear()
