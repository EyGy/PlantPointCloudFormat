# Plant Point Cloud Format (PPF)

[![Specification Version](https://img.shields.io/badge/PPFv1.0-documentation-blue.svg)](SPECIFICATION.md)

**A standardized format for 3D plant point clouds in phenotyping and agricultural applications.**


---

## Overview

PPF defines a consistent, interoperable format for representing individual plant point clouds with a unified format with semantic- and instance segmentation labels

PPF is built on the widely-supported PLY format with structured metadata conventions and compatible with all .ply viewers.

See full format specification --> [![Specification Version](https://img.shields.io/badge/PPFv1.0-documentation-blue.svg)](SPECIFICATION.md)
---

## Quick Start

### Installation / Requirements

```bash
pip install !!TODO!!
```

### Reading a PPF File

```python
TODO
```

### Loading a Dataset

```python
TODO
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [SPECIFICATION.md](SPECIFICATION.md) | Complete format specification |
| [examples/](examples/) | Example files and datasets |
| [reference/](reference/) | Python reference implementation |



---
## Key Features

### Standardized Coordinate System

All PPF point clouds use:
- **Unit**: Millimeters (mm)
- **Up axis**: Z-positive
- **Origin**: Median-centered (median of X, Y, Z coordinates)

### Semantic and Instance Labels follow panoptic labeling schema

```
semantic_label=1 (leaf), instance_id=5  ->  "Leaf instance #5"
semantic_label=8 (pot), instance_id=0  ->  "Pot (stuff class)"
```

## FAQs
| Document | Description |
|----------|-------------|
| What is this the reason behind and the purpose of PPF? | PPF was created to establish a simple unified data format for AI/ML based plant organ segmentation. Basically we got tired of spending days on dataset conversion for data loaders and want to create a benchmark dataset that works for everyone.
| Why not just use PLY as-is? |	PLY has no conventions for semantic labels, instance IDs, or plant metadata. PPF adds structure without breaking compatibility.|
| Why not HDF5? |	HDF5 is powerful but has no ecosystem overlap with point cloud tools (CloudCompare, Open3D). PPF files open in any PLY viewer.
| Why Median-Centered origin instead e.g. using the plant emergence point? | Median-centered origin is robust to outliers and computable without labels. Being able to position unlabeled data the same way as labeled data is crucial for downstream applications of any AI/ML application.

---
## Planned Extensions

- **Creation of Benchmark Dataset** for semantic and instance segmentation based on openly available datasets
- **Spatio-Temporal (time-series) dataset support**
- **Hierarchical organ relationships**

In the future we will also consider extending this format to support tree and forestry data.

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Ways to Contribute

- Report issues or suggest improvements
- Improve documentation
- Convert existing datasets to PPF to contribute to the creation of a plant point cloud segmentation benchmark

## Citation

If you use PPF in your research, please cite:

```bibtex
@misc{ppf2026,
  title={TODO: ADD PAPER HERE},
  author={[]},
  year={},
  url={https://github.com/EyGy/PlantPointCloudFormat}
}
```

---

## License
This work is part of a doctoral research project funded by Fraunhofer Institute for Integrated Circuits (IIS). It is currently in a pre-release version and the licensing discussion has not been finalized. Contact the author for any questions before the first official release. --> andreas.gilson@iis.fraunhofer.de

License TODO

---

## Acknowledgments

[TODO: Acknowledge contributors, funding, related projects]
Add all Authors of contributing datasets

---

## Contact

- **Issues**: [GitHub Issues](https://github.com/EyGy/PlantPointCloudFormat/issues)
- **Discussions**: [GitHub Discussions](https://github.com/EyGy/PlantPointCloudFormat/discussions)

