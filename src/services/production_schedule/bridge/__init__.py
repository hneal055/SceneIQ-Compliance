# =============================================================================
# src/services/production_schedule/bridge/__init__.py
# Marks the 'bridge' folder as a Python package.
# Holds the ComplianceBridge â€” the seam between the production schedule
# engine (scenes / shoot days / verified jurisdiction counts) and the
# existing SceneIQ compliance stack (Incentive Calculator, MMB
# Connector). All bridge code is pure compute; the Phase 10 router
# owns DB I/O on either side.
# =============================================================================

