"""Tests for the shop's JSON supply catalogue (shop/ folder)."""
import json

from athas.inventory_manager import load_shop_catalogue


def _write(folder, name, payload):
    path = folder / name
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_reads_single_items_and_lists(tmp_path):
    _write(tmp_path, "bandage.json", {
        "id": "bandage", "name": "Bandage", "price": 50,
        "description": "Stops bleeding.",
    })
    _write(tmp_path, "bundle.json", [
        {"id": "arrow", "name": "Arrow", "price": 5},
        {"id": "rope", "name": "Rope", "price": 20},
    ])
    catalogue = load_shop_catalogue(tmp_path)
    by_id = {entry["id"]: entry for entry in catalogue}
    assert by_id["bandage"]["price"] == 50
    assert by_id["arrow"]["name"] == "Arrow"
    assert by_id["rope"]["price"] == 20


def test_wrapped_items_format_and_default_id(tmp_path):
    _write(tmp_path, "crate.json", {"items": [
        {"name": "Torch", "price": 10},
    ]})
    (entry,) = load_shop_catalogue(tmp_path)
    assert entry["id"] == "crate"  # id defaults to the file stem


def test_templates_and_bad_files_are_skipped(tmp_path):
    _write(tmp_path, "_template.json", {"name": "Template", "price": 1})
    _write(tmp_path, "broken.json", "{not json at all")
    _write(tmp_path, "free.json", {"name": "Free", "price": 0})       # no price
    _write(tmp_path, "anon.json", {"price": 10})                      # no name
    _write(tmp_path, "aaa.json", {"id": "aaa", "name": "First", "price": 1})
    _write(tmp_path, "dup.json", {"id": "aaa", "name": "Dup", "price": 1})  # same id
    _write(tmp_path, "good.json", {"id": "good", "name": "Good", "price": 1})
    _write(tmp_path, "notes.txt", "not json")                         # wrong suffix
    catalogue = load_shop_catalogue(tmp_path)
    assert [entry["id"] for entry in catalogue] == ["aaa", "good"]


def test_missing_folder_is_empty(tmp_path):
    assert load_shop_catalogue(tmp_path / "nope") == []


def test_manager_uses_the_folder_with_built_in_fallback(tmp_path):
    from athas.inventory_manager import InventoryManager, SUPPLIES
    # No shop folder → the built-in supplies remain available.
    mgr = InventoryManager(
        items_dir=tmp_path / "items",
        library_dir=tmp_path / "library",
        cache_dir=tmp_path / "cache",
        rp_root=tmp_path,
    )
    assert mgr.supply_catalog() == SUPPLIES
    assert mgr.buy_supply("bandage") is not None
    # A shop folder replaces the catalogue.
    shop = tmp_path / "shop"
    shop.mkdir()
    _write(shop, "walter.json", {"id": "walter", "name": "Walter", "price": 42})
    mgr2 = InventoryManager(
        items_dir=tmp_path / "items",
        library_dir=tmp_path / "library",
        cache_dir=tmp_path / "cache",
        rp_root=tmp_path,
        shop_dir=shop,
    )
    assert [entry["id"] for entry in mgr2.supply_catalog()] == ["walter"]
    assert mgr2.buy_supply("walter") is not None
    assert mgr2.buy_supply("bandage") is None  # built-ins are replaced
