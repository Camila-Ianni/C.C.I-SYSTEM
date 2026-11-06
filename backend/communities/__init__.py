"""
backend/communities - Módulo de comunidades, roles y canales para C.C.I. SYSTEM.
"""
from backend.communities.repository import CommunitiesRepository
from backend.communities.service import CommunitiesService

__all__ = ["CommunitiesRepository", "CommunitiesService"]
