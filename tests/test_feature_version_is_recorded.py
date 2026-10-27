"""Guard: prediction rows must record the actual feature version produced
by the builder, not whatever the config happens to say."""

from data.features import FEATURE_VERSION


def test_feature_version_matches_builder_constant():
    # The builder exposes FEATURE_VERSION. Config's feature_version must be
    # allowed to differ, but log_prediction is called with features.feature_version.
    # This test simply pins the constant.
    assert FEATURE_VERSION == "features-v0.2.0"