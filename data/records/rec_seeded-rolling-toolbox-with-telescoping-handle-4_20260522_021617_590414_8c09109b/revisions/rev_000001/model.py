from __future__ import annotations

from agent.templates.rolling_toolbox_with_telescoping_handle import (
    build_rolling_toolbox,
    config_from_seed,
    run_rolling_toolbox_tests,
)
from sdk import AssetContext

SEED = 4
CONFIG = config_from_seed(SEED)
ASSETS = AssetContext.from_script(__file__)


def build_object_model():
    return build_rolling_toolbox(CONFIG, assets=ASSETS)


def run_tests():
    return run_rolling_toolbox_tests(object_model, CONFIG)


object_model = build_object_model()
