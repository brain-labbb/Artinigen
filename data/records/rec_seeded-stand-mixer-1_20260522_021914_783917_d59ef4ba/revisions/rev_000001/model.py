from __future__ import annotations

from agent.templates.stand_mixer import (
    build_stand_mixer,
    config_from_seed,
    run_stand_mixer_tests,
)
from sdk import AssetContext

SEED = 1
CONFIG = config_from_seed(SEED)
ASSETS = AssetContext.from_script(__file__)


def build_object_model():
    return build_stand_mixer(CONFIG, assets=ASSETS)


def run_tests():
    return run_stand_mixer_tests(object_model, CONFIG)


object_model = build_object_model()
