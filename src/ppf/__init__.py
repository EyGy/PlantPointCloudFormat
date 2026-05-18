"""
PPF — Plant Point Cloud Format (v1.0)

A self-documenting point cloud format for plant phenotyping research.
Reference implementation for reading, writing, and validating PPF files.

Specification: https://github.com/EyGy/PlantPointCloudFormat/blob/main/SPECIFICATION.md

Note: Parts of this reference implementation were co-developed with the
assistance of Claude Opus 4.6 (Anthropic). All code has been reviewed and tested
by the maintainers. It is not entirely vibe-coded, but created with AI assistance.
"""
from .ppf import PPFPointCloud, LabelDefinition, DEFAULT_LABELS, DEFAULT_LABEL_BY_ID, DEFAULT_LABEL_BY_NAME

from .io import read_ppf, write_ppf
from .validate import validate_ppf, ValidationResult

__version__ = "1.0.0"
__all__ = [
    "PPFPointCloud",
    "LabelDefinition",
    "read_ppf",
    "write_ppf",
    "validate_ppf",
    "ValidationResult",
]