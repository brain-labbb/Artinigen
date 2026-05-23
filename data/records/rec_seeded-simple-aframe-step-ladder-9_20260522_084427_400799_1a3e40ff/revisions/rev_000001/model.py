from __future__ import annotations

from agent.templates.simple_aframe_step_ladder import (
    build_simple_aframe_step_ladder,
    config_from_seed,
    run_simple_aframe_step_ladder_tests,
)
from sdk import AssetContext

SEED = 9
CONFIG = config_from_seed(SEED)
ASSETS = AssetContext.from_script(__file__)


def build_object_model():
    return build_simple_aframe_step_ladder(CONFIG, assets=ASSETS)


def run_tests():
    return run_simple_aframe_step_ladder_tests(object_model, CONFIG)


object_model = build_object_model()
