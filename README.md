# Plant Point Cloud Format (PPF)

[![Specification Version](https://img.shields.io/badge/spec-v1.0--draft-blue.svg)](SPECIFICATION.md)
[![License]ToDo ](LICENSE)

**A standardized format for plant point clouds in phenotyping and agricultural applications.**

---

## Overview

PPF defines a consistent, interoperable format for representing individual plant point clouds with:

- **Unified and structured format individual plant scans**
- **Semantic and instance segmentation labels**
- **Spatio-Temporal (time-series) dataset support**
- **Hierarchical organ relationships**
- **Rich metadata** for reproducible research

Built on the widely-supported PLY format with structured metadata conventions.

---

## Quick Start

### Installation / Requirements

```bash
pip install numpy plyfile
```

### Reading a PPF File

```python
from reference.ppf_io import read_ppf

cloud = read_ppf("plant_001.ply")
print(f"Plant: {cloud.plant_id}")
print(f"Points: {cloud.n_points}")
print(f"Has labels: {cloud.has_labels}")
```

### Loading a Dataset

```python
from reference.ppf_dataset import PPFDataset

dataset = PPFDataset.load("path/to/dataset")
train_subjects = dataset.get_split("train")
train_plants = dataset.get_plants_for_subjects(train_subjects)

for plant_entry in train_plants:
    cloud = dataset.load_plant(plant_entry)
    # Process cloud...
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [SPECIFICATION.md](SPECIFICATION.md) | Complete format specification |
| [examples/](examples/) | Example files and datasets |
| [reference/](reference/) | Python reference implementation |
| [templates/](templates/) | Templates for creating new datasets |

---

## Key Features

### Standardized Coordinate System

All PPF point clouds use:
- **Unit**: Millimeters (mm)
- **Up axis**: Z-positive
- **Origin**: Median-centered (median of X, Y, Z coordinates)

### Semantic and Instance Labels

```
semantic_label=1 (leaf), instance_id=5  ->  "Leaf instance #5"
semantic_label=2 (stem), instance_id=0  ->  "Stem (stuff class)"
```

### Temporal Dataset Support

Track plants across time with subject_id to prevent data leakage:

```python

# Correct: split by physical plant

train_subjects, test_subjects = train_test_split(all_subject_ids)

# All timepoints of a plant stay together

```

### Hierarchical Labels (Optional)

Model organ relationships like leaflet -> leaf -> branch:

```
organ_id links instances to their parent structures
```

---

## File Format Summary

### Minimal PLY Header

```ply
ply
format binary_little_endian 1.0
comment ppf_version 1.0
comment plant_id example_001
element vertex 50000
property float x
property float y
property float z
end_header
```

### Dataset Structure

```
dataset/
├── dataset.json      # Index and metadata
├── schema.json       # Label definitions
├── plants/           # PLY files
└── splits/           # train.txt, val.txt, test.txt
```

---

## Recommended Label IDs

For interoperability, use these IDs for common classes:

| ID | Name | Type |
|----|------|------|
| 0 | unlabeled | void |
| 1 | leaf | thing |
| 2 | stem | thing |
| 3 | petiole | thing |
| 4 | flower | thing |
| 5 | fruit | thing |
| 6 | root | thing |
| 7 | medium (e.g. soil, rockwool) | stuff |
| 8 | pot | stuff | 

See [templates/schema_template.json](templates/schema_template.json) for a starting point.

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Ways to Contribute

- Report issues or suggest improvements
- Improve documentation
- Extend the reference implementation
- Convert existing datasets to PPF
- Share your use cases

---

## Citation

If you use PPF in your research, please cite:

```bibtex
@misc{ppf2024,
  title={Plant Point Cloud Format (PPF): A Standardized Format for Plant Phenotyping},
  author={[Authors]},
  year={2024},
  url={https://github.com/[username]/ppf-specification}
}
```

---

## License

This specification is released under [CC-BY-4.0](LICENSE).

The reference implementation is released under [MIT License](reference/LICENSE).

---

## Acknowledgments

[TODO: Acknowledge contributors, funding, related projects]

---

## Contact

- **Issues**: [GitHub Issues](https://github.com/[username]/ppf-specification/issues)
- **Discussions**: [GitHub Discussions](https://github.com/[username]/ppf-specification/discussions)
- **Email**: [TODO]
