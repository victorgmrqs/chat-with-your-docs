"""Deliberately failing test (CWYD-6 failure proof). This branch is never merged."""


def test_ci_blocks_publishing_when_a_check_fails() -> None:
    assert 1 == 2, "deliberate failure: a failed check must block image build and publishing"
