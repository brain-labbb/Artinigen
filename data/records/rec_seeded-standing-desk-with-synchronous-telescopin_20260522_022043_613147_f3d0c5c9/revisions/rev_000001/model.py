from __future__ import annotations

from agent.templates.standing_desk_with_synchronous_telescoping_legs_and_articulated_controls import (
    build_standing_desk,
    config_from_seed,
    run_standing_desk_tests,
)
from sdk import AssetContext

SEED = 5
CONFIG = config_from_seed(SEED)
ASSETS = AssetContext.from_script(__file__)


def build_object_model():
    return build_standing_desk(CONFIG, assets=ASSETS)


def run_tests():
    return run_standing_desk_tests(object_model, CONFIG)


object_model = build_object_model()
