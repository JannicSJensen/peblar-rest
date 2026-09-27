"""Focused package contract tests."""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "peblar_rest"


def load_json(path: Path) -> dict:
    """Load a JSON object."""
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def test_manifest_is_hacs_compatible_and_collision_free() -> None:
    """The package must use its own domain and pinned maintained client."""
    manifest = load_json(COMPONENT / "manifest.json")
    assert manifest["domain"] == "peblar_rest"
    assert manifest["domain"] not in {"peblar", "peblar_modbus"}
    assert manifest["version"] == "0.1.1"
    assert manifest["requirements"] == ["mashumaro>=3.10", "tenacity>=8.0.0"]
    assert not any(req.startswith("peblar") for req in manifest["requirements"])
    assert manifest["iot_class"] == "local_polling"
    assert manifest["config_flow"] is True
    assert load_json(ROOT / "hacs.json")["render_readme"] is True


def test_all_python_files_parse() -> None:
    """Every integration module must be valid Python."""
    for path in COMPONENT.glob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_translations_match_strings() -> None:
    """English translations must stay synchronized with canonical strings."""
    assert load_json(COMPONENT / "strings.json") == load_json(
        COMPONENT / "translations" / "en.json"
    )


def test_all_platforms_are_present() -> None:
    """Every advertised entity platform must exist."""
    expected = {
        "binary_sensor.py",
        "button.py",
        "number.py",
        "select.py",
        "sensor.py",
        "switch.py",
        "update.py",
    }
    assert expected <= {path.name for path in COMPONENT.iterdir()}


def test_custom_solar_compatibility_is_wired() -> None:
    """Firmware 1.10 Custom Solar fields must be represented in controls."""
    select_source = (COMPONENT / "select.py").read_text(encoding="utf-8")
    number_source = (COMPONENT / "number.py").read_text(encoding="utf-8")
    switch_source = (COMPONENT / "switch.py").read_text(encoding="utf-8")
    assert "custom_solar" in select_source
    assert "solar_charging_custom_power_target" in number_source
    assert "solar_charging_custom_power_threshold" in number_source
    assert "solar_charging_custom_always_charge" in switch_source


def test_diagnostics_redact_credentials_and_identifiers() -> None:
    """Diagnostics must redact secrets and identifying network data."""
    source = (COMPONENT / "diagnostics.py").read_text(encoding="utf-8")
    for key in (
        "password",
        "host",
        "product_serial_number",
        "ethernet_mac_address",
        "wlan_mac_address",
        "customer_id",
        "bop_source_parameters",
        "solar_charging_source_parameters",
        "user_defined_household_power_limit_source_parameters",
    ):
        assert f'"{key}"' in source


def test_update_checks_uncached_versions_and_reboot_recovery() -> None:
    """Update handling must enforce package order and wait for a real reboot."""
    source = (COMPONENT / "update.py").read_text(encoding="utf-8")
    assert "available_versions(" in source
    assert "use_cache=False" in source
    assert "offline_since" in source
    assert "asyncio.sleep(10)" in source


def test_charge_limit_uses_restore_number() -> None:
    """Paused charging must retain the selected current across restarts."""
    source = (COMPONENT / "number.py").read_text(encoding="utf-8")
    assert "RestoreNumber" in source
    assert "async_get_last_number_data" in source


def test_integration_does_not_import_shared_peblar_package() -> None:
    """Use the vendored client so Home Assistant's bundled peblar is untouched."""
    for path in COMPONENT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 0:
                assert (node.module or "").split(".")[0] != "peblar", path
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] != "peblar", path
