from __future__ import annotations

from agent.templates.refrigerator_with_hinged_doors import (
    build_refrigerator,
    config_from_seed,
    run_refrigerator_tests,
)
from sdk import AssetContext

SEED = 1
CONFIG = config_from_seed(SEED)
ASSETS = AssetContext.from_script(__file__)


def build_object_model():
    return build_refrigerator(CONFIG, assets=ASSETS)


def run_tests():
    return run_refrigerator_tests(object_model, CONFIG)


object_model = build_object_model()
