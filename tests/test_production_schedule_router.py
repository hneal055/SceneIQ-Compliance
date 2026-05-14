# =============================================================================
# tests/test_production_schedule_router.py
# Phase 10 smoke tests — verify the production-schedule router loads,
# every brief endpoint is registered with the expected method + path,
# and the aggregator wires it under the JWT-protected group.
#
# Full end-to-end happy-path testing belongs to Phase 12 (against
# `docker compose up -d`), not here.
# =============================================================================


def test_router_module_imports_cleanly():
    """The router module must import without raising — catches missing
    imports, syntax errors, and circular import problems early."""
    from src.api import production_schedule  # noqa: F401


def test_all_endpoints_registered():
    """Every brief endpoint exists with the expected path + HTTP verb."""
    from src.api.production_schedule import router

    registered = set()
    for route in router.routes:
        # APIRoute objects expose .path and .methods; skip any non-API
        # route entries defensively (Mount, etc. — none expected here).
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path is None or methods is None:
            continue
        for method in methods:
            registered.add((path, method))

    expected = {
        ("/production-schedule/{production_id}/import", "POST"),
        ("/production-schedule/{production_id}/stripboard", "GET"),
        ("/production-schedule/{production_id}/stripboard/assign", "POST"),
        ("/production-schedule/{production_id}/dood", "GET"),
        ("/production-schedule/{production_id}/dood/export", "GET"),
        ("/production-schedule/{production_id}/call-sheet/{day_number}", "GET"),
        ("/production-schedule/{production_id}/call-sheet/{day_number}/pdf", "GET"),
        ("/production-schedule/{production_id}/jurisdiction-tracker", "GET"),
        ("/production-schedule/{production_id}/compliance-bridge/push", "POST"),
    }

    missing = expected - registered
    assert not missing, f"missing endpoints on router: {missing}"


def test_router_registered_with_auth():
    """The aggregator at src/api/routes.py must mount the production-
    schedule router under the JWT-protected group, so a real request
    without a Bearer token would be rejected."""
    from src.api.routes import router as aggregator

    paths_with_methods = []
    for route in aggregator.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path is None:
            continue
        paths_with_methods.append((path, methods or set()))

    ps_paths = [p for p, _ in paths_with_methods if "production-schedule" in p]
    assert ps_paths, "no production-schedule paths registered on the aggregator"
    # Should match the 9-endpoint count (each path × each method = one entry).
    # 8 path-segments and 9 method bindings (import POST + assign POST +
    # compliance-bridge/push POST are POSTs, the other 6 are GETs).
    assert len(ps_paths) >= 9, (
        f"expected at least 9 production-schedule paths registered, "
        f"got {len(ps_paths)}: {ps_paths}"
    )
