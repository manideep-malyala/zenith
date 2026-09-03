"""Unit tests verifying top-level zenith public package exports."""


def test_zenith_top_level_import():
    """Verify that ScanPipeline and PipelineContext are importable directly from zenith."""
    from zenith import PipelineContext, ScanPipeline, __version__

    assert ScanPipeline is not None
    assert PipelineContext is not None
    assert __version__ == "1.0.0"


def test_zenith_submodule_import():
    """Verify that zenith submodules can be accessed via import syntax."""
    import zenith.graph
    import zenith.pipeline

    assert zenith.pipeline is not None
    assert zenith.graph is not None
