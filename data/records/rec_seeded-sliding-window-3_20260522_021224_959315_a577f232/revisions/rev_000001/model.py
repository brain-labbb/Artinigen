from __future__ import annotations

from agent.templates.sliding_window import (
    build_sliding_window,
    config_from_seed,
    run_sliding_window_tests,
)
from sdk import AssetContext

SEED = 3
CONFIG = config_from_seed(SEED)
ASSETS = AssetContext.from_script(__file__)


def build_object_model():
    return build_sliding_window(CONFIG, assets=ASSETS)


def run_tests():
    return run_sliding_window_tests(object_model, CONFIG)


object_model = build_object_model()
