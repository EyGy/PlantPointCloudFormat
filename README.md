# Plant Point Cloud Format (PPF)

[![Specification Version](https://img.shields.io/badge/PPFv1.0-documentation-blue.svg)](SPECIFICATION.md) [![Example Notebook](https://img.shields.io/badge/PPFv1.0-example_Notebook-green.svg)](examples/ppf_example_notebook.ipynb)

**A standardized format for 3D plant point clouds in phenotyping and agricultural applications.**


---

## Overview

PPF defines a consistent, interoperable way of representing individual plant point clouds with semantic and instance segmentation labels in a unified format.

PPF is built on the widely-supported PLY format with structured metadata conventions and compatible with all .ply viewers.

See full format specification --> [![Specification Version](https://img.shields.io/badge/PPFv1.0-documentation-blue.svg)](SPECIFICATION.md)

---
## Key Features

### Standardized Coordinate System

All PPF point clouds use:
- **Unit**: Millimeters (mm)
- **Up axis**: Z-positive
- **Origin**: Median-centered (median of X, Y, Z coordinates)

### Semantic and Instance Labels follow panoptic labeling scheme

```
semantic_label=1 (leaf), instance_id=5  ->  "Leaf instance #5"
semantic_label=9 (pot), instance_id=0  ->  "Pot (stuff class)"
```
---
## Installation

### From GitHub (recommended for now)

```bash
pip install git+https://github.com/EyGy/PlantPointCloudFormat.git
```
### From PyPI (upon 1st stable release)
```bash
[! NOT AVAILABLE YET] pip install ppf
```
## Quick Start
Refer to the [Example Notebook](examples/ppf_example_notebook.ipynb) for a preview. 
#### Reading a PPF file

```python
import ppf

plant = ppf.read_ppf(filepath="examples/example_begonia_ppf.ply")
```


#### Restoring metadata / PPF headers
Editing PPF files with viewers like CloudCompare or Meshlab will overwrite PPF metadata. To avoid this save the edited point cloud separately and use this function to restore metadata:
```python
ppf.transfer_metadata(edited, original, output)
```
---
#### Validating a PPF file via CLI
For a quick format check it is possible to use the CLI interface:
```bash
ppf-validate ../examples/example_begonia_ppf.ply
```
Example CLI output:
```bash
  [WARN]  Missing recommended field: 'plant_category'
  [INFO]  No custom labels defined — using PPF base schema for interpretation.
  [INFO]  200,000 points
  [INFO]  0 label(s) defined
  [INFO]  Has RGB colors
```
---

## Documentation

| Document | Description |
|----------|-------------|
| [SPECIFICATION.md](SPECIFICATION.md) | Complete format specification |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |
| [examples/](examples/) | Example files and notebook |
| [src/](src/) | Python implementation |



---


## FAQs
| Document | Description |
|----------|-------------|
| What is the reason behind PPF? | PPF was created to establish a simple unified data format for AI/ML based plant organ segmentation. Basically we got tired of spending days on dataset conversion for data loaders and want to create a benchmark dataset that works for everyone.
| Why not just use PLY as-is? |	PLY has no conventions for semantic labels, instance IDs, or plant metadata. PPF adds structure without breaking compatibility.|
| Why not HDF5? |	HDF5 is powerful but has no ecosystem overlap with point cloud tools (CloudCompare, Open3D). PPF files open in any PLY viewer.
| Why Median-Centered origin instead e.g. using the plant emergence point? | Median-centered origin is robust to outliers and computable without labels. Being able to position unlabeled data the same way as labeled data is crucial for downstream applications of any AI/ML application.
| What file ending should is use? | We recommend saving your files as .ply to ensure compatibility with the PLY ecosystem. To signal a ppf header it is best practice to save you file as "filename_pff.ply"|

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


## Acknowledgments

This work is part of a doctoral research project funded by Fraunhofer Institute for Integrated Circuits (IIS) and supported by Cognitive Systems chair at the University of Bamberg. It is currently in a pre-release version and not finalized. 

Please contact the author for any questions before the first official release. --> andreas.gilson@iis.fraunhofer.de


---

## Contact

- **Issues**: [GitHub Issues](https://github.com/EyGy/PlantPointCloudFormat/issues)
- **Discussions**: [GitHub Discussions](https://github.com/EyGy/PlantPointCloudFormat/discussions)

