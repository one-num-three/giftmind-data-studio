from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).parents[2]
    / "skills"
    / "giftmind-gift-ingest"
    / "scripts"
    / "ingest_gift.py"
)
SPEC = importlib.util.spec_from_file_location("giftmind_ingest_client", SCRIPT_PATH)
assert SPEC and SPEC.loader
CLIENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLIENT)


def parse(monkeypatch: pytest.MonkeyPatch, *arguments: str):
    monkeypatch.setattr(sys, "argv", ["ingest_gift.py", *arguments])
    return CLIENT.parse_args()


def test_builds_verified_taobao_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    args = parse(
        monkeypatch,
        "--name",
        "自由飞鸟杯子礼盒",
        "--generic-product-name",
        "杯子礼盒",
        "--material",
        "陶瓷",
        "--color",
        "蓝色",
        "--size",
        "常规",
        "--taobao-shop-name",
        "FLOW自由飞鸟商店",
        "--taobao-item-id",
        "870922947672",
        "--taobao-sku",
        "颜色=蓝色",
        "--taobao-sku",
        "包装=礼盒装",
        "--taobao-price",
        "158",
        "--taobao-observed-at",
        "2026-08-05T17:30:00+08:00",
    )

    known = CLIENT.load_known_fields(args)

    assert known["priceMin"] == 158
    assert known["priceMax"] == 158
    details = known["productDetails"]
    assert details["materials"] == ["陶瓷"]
    assert details["colors"] == ["蓝色"]
    evidence = details["specifications"]["taobaoEvidence"]
    assert evidence["shopName"] == "FLOW自由飞鸟商店"
    assert evidence["selectedSku"] == {"颜色": "蓝色", "包装": "礼盒装"}
    assert evidence["priceEvidence"] == "detail-sku"
    assert "详情页价格=CNY 158" in known["sourceNotes"]


def test_client_defaults_to_local_analysis(monkeypatch: pytest.MonkeyPatch) -> None:
    args = parse(monkeypatch)

    assert args.analysis_mode == "local"


def test_local_mode_server_version_gate() -> None:
    assert CLIENT.version_tuple("1.1.0") >= CLIENT.LOCAL_MODE_MIN_SERVER_VERSION
    assert CLIENT.version_tuple("1.0.9") < CLIENT.LOCAL_MODE_MIN_SERVER_VERSION
    assert CLIENT.version_tuple("invalid") == (0, 0, 0)


def test_taobao_price_requires_selected_sku(monkeypatch: pytest.MonkeyPatch) -> None:
    args = parse(monkeypatch, "--taobao-price", "99")

    with pytest.raises(ValueError, match="requires at least one --taobao-sku"):
        CLIENT.load_known_fields(args)


def test_taobao_price_requires_observation_time(monkeypatch: pytest.MonkeyPatch) -> None:
    args = parse(monkeypatch, "--taobao-sku", "颜色=蓝色", "--taobao-price", "99")

    with pytest.raises(ValueError, match="requires --taobao-observed-at"):
        CLIENT.load_known_fields(args)


def test_taobao_observation_requires_timezone(monkeypatch: pytest.MonkeyPatch) -> None:
    args = parse(
        monkeypatch,
        "--taobao-item-id",
        "123",
        "--taobao-observed-at",
        "2026-08-05T17:30:00",
    )

    with pytest.raises(ValueError, match="must include a timezone"):
        CLIENT.load_known_fields(args)
