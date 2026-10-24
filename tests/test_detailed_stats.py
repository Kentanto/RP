from athas.artifact_generator import MAIN_STATS
from athas.detailed_stats import (
    LEVEL_GROWTH,
    STAT_CAPABILITY_RANGES,
    capability_comparison,
    level_multiplier,
    measured_stat_values,
    total_dg_rating,
    _fmt_measurement,
)


def _totals(**over):
    totals = {key: {"base": 0, "temp": 0, "artifact": 0, "total": 0} for key in MAIN_STATS}
    for key, total in over.items():
        totals[key] = {"base": total, "temp": 0, "artifact": 0, "total": total}
    return totals


def test_level_growth_is_1_10_per_level():
    assert LEVEL_GROWTH == 1.05
    assert level_multiplier(1) == 1.0
    assert abs(level_multiplier(2) - 1.1) < 1e-9
    assert abs(level_multiplier(12) - 1.1 ** 11) < 1e-9


def test_capability_comparison_uses_the_matching_attack_band():
    assert capability_comparison("attack", 999.9) == STAT_CAPABILITY_RANGES["attack"][0][2]
    assert capability_comparison("attack", 1000) == STAT_CAPABILITY_RANGES["attack"][1][2]


def test_capability_comparison_uses_open_ended_final_band():
    assert capability_comparison("attack", 300_000) == STAT_CAPABILITY_RANGES["attack"][-1][2]


def test_capability_ranges_cover_zero_and_negative_measurements():
    assert capability_comparison("speed", 0) == STAT_CAPABILITY_RANGES["speed"][0][2]
    assert capability_comparison("speed", -1) == "Below the listed reference ranges."


def test_measurements_are_linear_dg_ratings():
    vals = measured_stat_values(_totals(attack=10), 1)
    assert vals["attack"]["value"] == 600.0  # 10 pts × 60 DG × 1.00
    assert vals["attack"]["unit"] == "DG"
    vals = measured_stat_values(_totals(attack=10, health=5), 3)
    assert abs(vals["attack"]["value"] - 10 * 60 * 1.1 ** 2) < 1e-6
    assert abs(vals["health"]["value"] - 5 * 60 * 1.1 ** 2) < 1e-6


def test_measurement_formatter_uses_dg():
    assert _fmt_measurement(36_765.0, "DG") == "36,765 DG"
    assert _fmt_measurement(600.0, "DG") == "600 DG"


def test_total_dg_rating_sums_all_stats():
    vals = measured_stat_values(_totals(attack=10, health=5), 1)
    assert total_dg_rating(vals) == 900.0  # 600 + 300
    vals = measured_stat_values(_totals(attack=10), 3)
    assert abs(total_dg_rating(vals) - 10 * 60 * 1.1 ** 2) < 1e-6


def test_total_capability_band_exists():
    assert capability_comparison("total", 80_457) == STAT_CAPABILITY_RANGES["total"][2][2]
    assert capability_comparison("total", 5_000) == STAT_CAPABILITY_RANGES["total"][0][2]
