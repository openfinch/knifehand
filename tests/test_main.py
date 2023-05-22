"""Test cases for the __main__ module."""
import numpy as np
import pytest
from click.testing import CliRunner
from numpy.typing import NDArray

from knifehand import detect_cut_signature
from knifehand.__main__ import main


@pytest.mark.parametrize(
    "frame, required_pixels, color_tolerance, expected",
    [
        # Frame with exactly the required pixels of each color
        (
            np.tile(
                np.array([[[0, 255, 255], [255, 0, 255], [255, 255, 0]]]), (20, 20, 1)
            ),
            10,
            30,
            True,
        ),
        # Frame with more than the required pixels of each color
        (
            np.tile(
                np.array([[[0, 255, 255], [255, 0, 255], [255, 255, 0]]]), (20, 20, 1)
            ),
            5,
            30,
            True,
        ),
        # Frame with colors within tolerance
        (
            np.tile(
                np.array([[[10, 245, 245], [245, 10, 245], [245, 245, 10]]]),
                (20, 20, 1),
            ),
            10,
            30,
            True,
        ),
        # Frame with less than the required pixels of each color
        (
            np.tile(
                np.array([[[0, 255, 255], [255, 0, 255], [255, 255, 0]]]), (20, 20, 1)
            ),
            500,
            30,
            False,
        ),
        # Frame with colors outside tolerance
        (
            np.tile(
                np.array([[[40, 215, 215], [215, 40, 215], [215, 215, 40]]]),
                (20, 20, 1),
            ),
            10,
            30,
            False,
        ),
        # Frame without the required colors
        (
            np.tile(
                np.array([[[0, 0, 0], [255, 255, 255], [127, 127, 127]]]), (20, 20, 1)
            ),
            10,
            30,
            False,
        ),
    ],
)
def test_detect_cut_signature(
    frame: NDArray[np.uint32],
    required_pixels: int,
    color_tolerance: int,
    expected: bool,
) -> None:
    """It returns True if the frame matches a cut signature, else False."""
    assert detect_cut_signature(frame, required_pixels, color_tolerance) == expected


def test_main_succeeds(runner: CliRunner) -> None:
    """It exits with a status code of zero."""
    result = runner.invoke(main)
    assert result.exit_code == 0
