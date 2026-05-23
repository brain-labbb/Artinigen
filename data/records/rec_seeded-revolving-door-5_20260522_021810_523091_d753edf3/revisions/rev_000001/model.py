from __future__ import annotations

from agent.templates.revolving_door import (
    build_revolving_door,
    config_from_seed,
    run_revolving_door_tests,
)
from sdk import AssetContext

SEED = 5
CONFIG = config_from_seed(SEED)
ASSETS = AssetContext.from_script(__file__)


def build_object_model():
    return build_revolving_door(CONFIG, assets=ASSETS)


def run_tests():
    return run_revolving_door_tests(object_model, CONFIG)


object_model = build_object_model()
