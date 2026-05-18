"""
ppf.validate — Validate PPF files against the v1.0 specification.

Usage:
    from ppf import validate_ppf

    result = validate_ppf("my_plant.ply")
    print(result)
    assert result.is_valid

CLI:
    ppf-validate my_plant.ply
    ppf-validate *.ply
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

import numpy as np

from .io import read_ppf
from .ppf import (
    MANDATORY_METADATA,
    RECOMMENDED_METADATA,
    PPFPointCloud,
)


@dataclass
class ValidationResult:
    """Result of PPF file validation."""

    filepath: str
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    info: list = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """File is valid if there are no errors."""
        return len(self.errors) == 0

    def __str__(self) -> str:
        lines = [f"{'VALID' if self.is_valid else 'INVALID'}: {self.filepath}"]
        for e in self.errors:
            lines.append(f"  [ERROR] {e}")
        for w in self.warnings:
            lines.append(f"  [WARN]  {w}")
        for i in self.info:
            lines.append(f"  [INFO]  {i}")
        return "\n".join(lines)


def validate_ppf(filepath: Union[str, Path]) -> ValidationResult:
    """Validate a PPF file against the v1.0 specification.

    Args:
        filepath: Path to the .ply file.

    Returns:
        ValidationResult with errors, warnings, and info messages.
    """
    filepath = Path(filepath)
    result = ValidationResult(filepath=str(filepath))

    if not filepath.exists():
        result.errors.append(f"File not found: {filepath}")
        return result

    if filepath.suffix.lower() != ".ply":
        result.warnings.append(f"Extension is '{filepath.suffix}', expected '.ply'")

    # Try reading
    try:
        cloud = read_ppf(filepath)
    except Exception as e:
        result.errors.append(f"Parse error: {e}")
        return result

    _check_metadata(cloud, result)
    _check_labels(cloud, result)
    _check_coordinates(cloud, result)
    _check_annotations(cloud, result)

    # Info summary
    result.info.append(f"{cloud.n_points:,} points")
    if cloud.has_annotations:
        result.info.append(f"{len(cloud.labels)} label(s) defined")
    if cloud.has_colors:
        result.info.append("Has RGB colors")

    return result


def _check_metadata(cloud: PPFPointCloud, result: ValidationResult):
    """Validate mandatory and recommended metadata."""
    for key in MANDATORY_METADATA:
        if key not in cloud.metadata:
            result.errors.append(f"Missing mandatory field: '{key}'")
        elif not cloud.metadata[key].strip():
            result.errors.append(f"Mandatory field '{key}' is empty")

    if "ppf_version" in cloud.metadata and cloud.metadata["ppf_version"] != "1.0":
        result.warnings.append(
            f"ppf_version is '{cloud.metadata['ppf_version']}', validator targets 1.0"
        )

    for key in RECOMMENDED_METADATA:
        if key not in cloud.metadata:
            result.warnings.append(f"Missing recommended field: '{key}'")


def _check_labels(cloud: PPFPointCloud, result: ValidationResult):
    if not cloud.labels:
        if cloud.has_annotations:
            result.info.append(
                "No custom labels defined — using PPF base schema for interpretation."
            )
        return

    # Duplicate IDs or names
    ids = [l.id for l in cloud.labels]
    if len(ids) != len(set(ids)):
        result.errors.append("Duplicate label IDs")

    names = [l.name for l in cloud.labels]
    if len(names) != len(set(names)):
        result.errors.append("Duplicate label names")

    # ID 0 should be void
    label_0 = cloud.get_label_by_id(0)
    if label_0 and label_0.type != "void":
        result.warnings.append(
            f"Label ID 0 ('{label_0.name}') is '{label_0.type}', convention is 'void'"
        )


def _check_coordinates(cloud: PPFPointCloud, result: ValidationResult):
    """Validate coordinate conventions."""
    if np.any(~np.isfinite(cloud.points)):
        n_bad = int(np.sum(~np.isfinite(cloud.points)))
        result.errors.append(f"{n_bad} non-finite values (NaN/Inf) in coordinates")
        return

    extent = cloud.points.max(axis=0) - cloud.points.min(axis=0)
    max_ext = float(extent.max())

    if max_ext > 100_000:
        result.warnings.append(
            f"Max extent is {max_ext:.0f} mm ({max_ext/1000:.1f} m) — "
            f"are coordinates in mm?"
        )
    elif max_ext < 1.0:
        result.warnings.append(
            f"Max extent is {max_ext:.4f} mm — might be in meters instead of mm?"
        )

    # Check centering
    median = np.median(cloud.points, axis=0)
    offset = float(np.linalg.norm(median))
    if offset > 1000:
        result.warnings.append(
            f"Median is {offset:.0f} mm from origin — consider median-centering."
        )


def _check_annotations(cloud: PPFPointCloud, result: ValidationResult):
    """Validate annotation consistency."""
    if not cloud.has_annotations:
        return

    # Check semantic IDs reference defined labels
    if cloud.labels:
        defined = {l.id for l in cloud.labels}
        used = set(np.unique(cloud.semantic_id).tolist())
        undefined = used - defined
        if undefined:
            result.warnings.append(
                f"semantic_id values {undefined} used but not defined in header"
            )

    # Check instance consistency with label types
    if cloud.has_instances and cloud.labels:
        for label in cloud.labels:
            mask = cloud.semantic_id == label.id
            if not np.any(mask):
                continue
            instances = np.unique(cloud.instance_id[mask])
            nonzero = instances[instances > 0]

            if label.type == "stuff" and len(nonzero) > 0:
                result.warnings.append(
                    f"'{label.name}' is 'stuff' but has instance_ids: "
                    f"{nonzero.tolist()}"
                )
            if label.type == "void" and len(nonzero) > 0:
                result.warnings.append(
                    f"'{label.name}' is 'void' but has instance_ids: "
                    f"{nonzero.tolist()}"
                )


# =============================================================================
# CLI
# =============================================================================


def main():
    """CLI entry point: ppf-validate <file.ply> [...]"""
    if len(sys.argv) < 2:
        print("Usage: ppf-validate <file.ply> [file2.ply ...]")
        sys.exit(1)

    all_valid = True
    for path in sys.argv[1:]:
        result = validate_ppf(path)
        print(result)
        print()
        if not result.is_valid:
            all_valid = False

    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()