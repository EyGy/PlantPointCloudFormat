"""Generate example PPF files for documentation.

Run: python examples/generate_examples.py
"""

import sys
from pathlib import Path

import numpy as np

# Add src to path for standalone execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ppf import PPFPointCloud, LabelDefinition, write_ppf, validate_ppf


def generate_minimal():
    """Minimal valid PPF file."""
    return PPFPointCloud(
        points=np.array(
            [[0.0, 0.0, 0.0],
             [1.0, 0.5, 2.0],
             [-1.0, 0.3, 4.0],
             [0.5, -0.5, 6.0],
             [0.0, 0.0, 8.0]],
            dtype=np.float32,
        ),
        metadata={"ppf_version": "1.0", "plant_id": "minimal_001"},
    )


def generate_full():
    """Fully-featured PPF file with annotations and colors."""
    np.random.seed(42)

    # Stem: vertical with noise
    n_stem = 40
    stem_z = np.linspace(0, 150, n_stem)
    stem_xy = np.random.normal(0, 1.5, (n_stem, 2))
    stem = np.column_stack([stem_xy, stem_z])

    # Leaves: 3 instances branching off
    leaves = []
    for i, (z_base, angle) in enumerate([(50, 0), (90, 2.1), (130, 4.2)]):
        n_leaf = 30
        t = np.linspace(0, 40, n_leaf)
        x = t * np.cos(angle) + np.random.normal(0, 1.0, n_leaf)
        y = t * np.sin(angle) + np.random.normal(0, 1.0, n_leaf)
        z = z_base + np.random.normal(0, 2.0, n_leaf)
        leaves.append(np.column_stack([x, y, z]))

    points = np.vstack([stem] + leaves).astype(np.float32)

    # Median-center
    points -= np.median(points, axis=0)

    n_total = n_stem + 3 * 30

    # Semantic + instance IDs
    semantic_id = np.zeros(n_total, dtype=np.int32)
    semantic_id[:n_stem] = 2  # stem
    semantic_id[n_stem:] = 1  # leaf

    instance_id = np.zeros(n_total, dtype=np.int32)
    instance_id[:n_stem] = 1  # stem instance
    for i in range(3):
        start = n_stem + i * 30
        end = start + 30
        instance_id[start:end] = i + 1

    # Colors
    colors = np.zeros((n_total, 3), dtype=np.uint8)
    colors[:n_stem] = [139, 90, 43]
    colors[n_stem:n_stem + 30] = [34, 180, 34]
    colors[n_stem + 30:n_stem + 60] = [50, 205, 50]
    colors[n_stem + 60:] = [0, 160, 0]

    return PPFPointCloud(
        points=points,
        metadata={
            "ppf_version": "1.0",
            "plant_id": "full_example_maize_001",
            "species": "Zea_mays",
            "acquisition_date": "2025-06-01",
            "acquisition_time": "14:30:00Z",
            "sensor_type": "lidar_terrestrial",
            "plant_category": "monocot",
            "dataset_name": "PPF_Examples",
            "growth_stage": "BBCH_14",
            "cultivar": "B73",
        },
        labels=[
            LabelDefinition(0, "unlabeled", "void"),
            LabelDefinition(1, "leaf", "thing"),
            LabelDefinition(2, "stem", "thing"),
        ],
        semantic_id=semantic_id,
        instance_id=instance_id,
        colors=colors,
    )


def main():
    out_dir = Path(__file__).parent
    out_dir.mkdir(exist_ok=True)

    # Minimal (ASCII for readability)
    minimal = generate_minimal()
    write_ppf(minimal, out_dir / "minimal_example.ply", encoding="ascii")
    print(f"  Written: minimal_example.ply")

    # Full (ASCII for readability + binary for distribution)
    full = generate_full()
    write_ppf(full, out_dir / "full_example.ply", encoding="ascii")
    write_ppf(full, out_dir / "full_example_binary.ply", encoding="binary_little_endian")
    print(f"  Written: full_example.ply")
    print(f"  Written: full_example_binary.ply")

    # Validate all
    print("\nValidation:")
    for f in out_dir.glob("*.ply"):
        result = validate_ppf(f)
        print(f"  {result}")


if __name__ == "__main__":
    main()