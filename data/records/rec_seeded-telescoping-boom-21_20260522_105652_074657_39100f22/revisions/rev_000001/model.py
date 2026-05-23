from __future__ import annotations

from agent.templates.telescoping_boom import (
    build_telescoping_boom,
    config_from_seed,
    run_telescoping_boom_tests,
)
from sdk import AssetContext

SEED = 21
CONFIG = config_from_seed(SEED)
ASSETS = AssetContext.from_script(__file__)


def build_object_model():
    return build_telescoping_boom(CONFIG, assets=ASSETS)


def run_tests():
    return run_telescoping_boom_tests(object_model, CONFIG)


object_model = build_object_model()
