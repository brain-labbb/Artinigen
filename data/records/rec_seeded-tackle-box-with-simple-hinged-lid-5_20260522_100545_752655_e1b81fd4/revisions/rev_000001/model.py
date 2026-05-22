from __future__ import annotations

from agent.templates.tackle_box_with_simple_hinged_lid import (
    build_tackle_box,
    config_from_seed,
    run_tackle_box_tests,
)
from sdk import AssetContext

SEED = 5
CONFIG = config_from_seed(SEED)
ASSETS = AssetContext.from_script(__file__)


def build_object_model():
    return build_tackle_box(CONFIG, assets=ASSETS)


def run_tests():
    return run_tackle_box_tests(object_model, CONFIG)


object_model = build_object_model()
