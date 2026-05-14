# Plant Point Cloud Format (PPF) Specification

**Version 1.0 — Draft 0.3 planned for a first conference submission in June 2026*

**Status**: Pre-Submission-Draft — Open for community feedback

**Last Updated**: 2026-05-14 (YYYY-MM-DD)

---

## Table of Contents

1. [Introduction and Motivation](#1-introduction-and-motivation)
2. [File Format Overview](#2-file-format-overview)
3. [PLY Header Specification](#3-ply-header-specification)
   - [3.1 Mandatory Fields](#31-mandatory-fields)
   - [3.2 Conditional Fields](#32-conditional-fields)
   - [3.3 Recommended Fields](#33-recommended-fields-include-when-information-is-available)
   - [3.4 Optional Extensions](#34-optional-extensions)
4. [Label Schema Format](#4-label-schema-format)
    - [Recommended Label Encoding](#41-recommended-base-schema)
    - [Custom Label Encoding](#42-custom-label-encoding-schema)
5. [Examples](#5-examples)
6. [Reference Implementation](#6-reference-implementation)
7. [Version History and Future Extensions](#7-version-history-and-future-extensions)
8. [Quick Checklist](#appendix-a-quick-reference)

---

## 1. Introduction and Motivation

### 1.1 Purpose

The Plant Point Cloud Format (PPF) is a standardized format for representing individual plant point clouds, designed specifically for plant phenotyping, agricultural research, and machine learning applications. Its purpose is to address current challenges in plant point cloud research like inconsistent annotations, missing metadata and time wasted on format conversion. PPF defines a consistent file structure based on PLY with standardized labels formats and flexible but structured metadata conventions. PPF is a free and non-commercial community project created by & for plant point cloud researchers with the goal of making all our lives easier trough on a common standard. Feel invited to suggest improvements or to contribute directly (see [CONTRIBUTING.md](CONTRIBUTING.md)).

#### Scope

**In scope (v1.0)**:
- Individual plant point clouds (one plant per file)
- Semantic and instance segmentation labels
- Self-documenting, standalone files (no external schema required to interpret a file)

**Planned extensions**:
- Hierarchical organ relationships
- Spatio-temporal (time-series) datasets
- Conversion of existing dataset for an upcoming benchmark release


**Out of scope (for now v1.0)**:
- Trees, forestry and orchard data (planned)
- Multi-spectral data
- Multi-plant scene representations
- Raw sensor and mesh data formats

---

## 2. File Format Overview

### 2.1 Base Format: PLY

PPF uses the **Polygon File Format (PLY)** as its base.
PLY files are supported by Open3D, trimesh, plyfile, CloudCompare, MeshLab, and many more.


### 2.2 Potential PPF file encodings

| Context | Encoding | Rationale |
|---------|----------|-----------|
| Distribution | binary_little_endian | Compact, fast |
| Debugging / Examples | ascii | Human-readable |

**Requirement**: PPF-compliant tools MUST support both encodings.


### 2.3 Coordinate System Conventions

**All PPF point clouds MUST use these conventions:**

| Property | Convention | Notes |
|----------|------------|-------|
| **Unit** | Millimeters (mm) | All XYZ coordinates are scaled in metrical millimeters |
| **Up axis** | Z-positive | Z axis increases upwards in plant growth direction |
| **Origin** | Median-centered | Origin at median(X), median(Y), median(Z) of the plant point cloud|

#### Why Median-Centered Origin?

- Computable without labels (works for unlabeled data)
- Robust to outliers
- Normalizes spatial distribution across plant architectures


### 2.4 One Plant Per File

Each PPF file represents **exactly one individual plant**.

Multi-plant scenes must be segmented into individual files.

---

## 3. PLY Header Specification

PPF stores all metadata as structured header comments:
```
comment key value
```
This ensures every file is self-documenting.



### 3.1 Mandatory Fields

#### 3.1.1 Header Comments

| Key | Type | Description | Example |
|-----|------|-------------|---------|
| ppf_version | string | Specification version | 1.0 |
| plant_id | string | Unique identifier for this scan | arabidopsis_001_t0 |

#### 3.1.2 Vertex Properties

| Property | Data Type | Description |
|----------|-----------|-------------|
| x | float | X coordinate (mm) |
| y | float | Y coordinate (mm) |
| z | float | Z coordinate (mm) |

#### 3.1.3 Minimal Valid Header

```ply
ply
format binary_little_endian 1.0
comment ppf_version 1.0
comment plant_id example_plant_001
element vertex 50000
property float x
property float y
property float z
end_header
```

### 3.2 Conditional Fields

#### 3.2.1 Annotation Vertex Property (required if annotated)

| Property | Data Type | Description |
|----------|-----------|-------------|
| semantic_id | int | Semantic class ID (see Section 4) |
| instance_id | int | Instance ID within semantic class |

**Instance ID conventions**:

| Value | Meaning |
|-------|---------|
| 0 / Missing / NaN | Unlabeled or "stuff" class (no instances) |
| 1, 2, 3, ... | Distinct instance IDs |

**Important**: Instance IDs are unique **within each semantic class**, not globally. An instance_id = 0 indicates that this element has no instance label (valid instance labels start counting with 1).
When annotating plants we recommend counting the instances bottom-top. Thus, the lowest leaf (closest to emergence point) gets instance_id = 1 and the most upper leaf gets instance_id = max.

This may be very difficult for dense plants - in that case try to follow this recommendation to the best of your ability.



### 3.3 Recommended Fields (include additional information)

#### 3.3.1 Header Comments

| Key | Type | Description | Example |
|-----|------|-------------|---------|
| species | string | Scientific name (underscore-separated) | Arabidopsis_thaliana |
| acquisition_date | string | ISO 8601 format | 2024-03-15 |
| acquisition_time | string | ISO 8601 format | 13:46:05Z |
| sensor_type | string | Acquisition modality | See vocabulary below |
| plant_category | string | Grouping to identify structurally similar plants | See vocabulary below |
| dataset_name | string | Parent dataset identifier | BonnBeetClouds |

**OPEN TODO: Plant category vocabulary**:

The suggested below distinction is not compatible with existing standards in biology. This needs adaptation!
| Value | Description |
|-------|-------------|
| monocot | Monocotyl plants (sorghum/maize/wheat) |
| dicot-rosette | Dicotyl plants with leafly structure close to the ground (strawberry, sugar beets) |
| dicot-bushy | Dicotyl plants with a bushy/woody structure (pepper, soy, rose, etc.)  |

**Sensor type vocabulary**:

| Value | Description |
|-------|-------------|
| lidar_terrestrial | Terrestrial laser scanning |
| lidar_mobile | Mobile/handheld LiDAR |
| sfm | Structure from Motion |
| structured_light | Structured light scanning |
| tof | Time-of-flight camera |
| rgb_d | RGB-D sensor |
| other | If you user other sensors, please contribute by extending this list!|

#### 3.3.2 Additional Vertex Properties

| Property | Data Type | Description |
|----------|-----------|-------------|
| red | uchar | Red channel (0-255) |
| green | uchar | Green channel (0-255) |
| blue | uchar | Blue channel (0-255) |
| intensity | float | Return intensity/reflectance |

**Notes**:
- Omit RGB properties entirely if unavailable (do not fill with zeros)
- Omit intensity if unavailable
- Both may coexist

### 3.4 Optional Extensions

#### 3.4.1 Header Comments

| Key | Type | Description | Example |
|-----|------|-------------|---------|
| growth_stage | string | BBCH code or DAE (Days after emergence) | BBCH_14, DAE_21 |
| cultivar | string | Cultivar/genotype | Col-0 |
| treatment | string | Experimental treatment | drought_stress |
| processing_level | string | Processing stage | raw, cleaned |
| source_file | string | Original filename | scan_001.las |
| other | Other/unspecified | |

#### 3.4.2 Vertex Properties

| Property | Data Type | Description |
|----------|-----------|-------------|
| nx | float | Normal X component |
| ny | float | Normal Y component |
| nz | float | Normal Z component |
| confidence | float | Prediction confidence (0.0-1.0) |

---

## 4. Label Schema Format


### 4.1 Recommended Base Schema

Use the following IDs for common classes to maximize interoperability. The IDs can be arbitrarilty extended with new custom classes as needed 
(e.g.: "class" leaflet with ID=11 or class "closed_bud" with ID=24). Avoid double ususage of already listed IDs for another class (even if the listed class is not present in your dataset).

| ID | Name | Type |
|----|------|------|
| 0 | unlabeled | void |
| 1 | leaf | thing |
| 2 | stem | thing |
| 3 | petiole | thing |
| 4 | flower | thing |
| 5 | fruit | thing |
| 6 | root | thing |
| 7 | medium (soil, coco, etc.)| stuff |
| 8 | pot | stuff |
---

***Important:*** If your data uses a different label encoding, it must be defined in the PLY header as proposed in [section 4.2](#42-custom-label-encoding-schema).

### 4.2 Custom Label Encoding Schema
Custom labels are defined directly in the PLY header. E.g. if you want to distinguish between different kind of leaves within one plant this could look like this:

```ply
comment label 0 unlabeled void
comment label 1 leaf thing
comment label 2 stem stuff
comment label 10 damaged_leaf thing
comment label 11 old_leaf thing
comment label 12 emerging_leaf thing
```
***Important:*** If no label schema is defined, the data will be interpreted according to the recommended base schema presented in [section 4.1](#41-recommended-base-schema). If you use custom labels it is highly recommended not override label IDs used in the base schema. While this is possible and supported by the PPF dataloader, it can lead to confusion and inconsistencies later on or when other researchers want to use your work.


## 5. Examples

See the examples/ directory for complete example files:

| Example | Description |
|---------|-------------|
| minimal_example.ply | Simplest valid PPF file |
| full_example.ply | All features demonstrated |

### 5.1 Minimal Example

```ply
ply
format ascii 1.0
comment ppf_version 1.0
comment plant_id minimal_001
element vertex 5
property float x
property float y
property float z
end_header
0.0 0.0 0.0
1.0 0.5 2.0
-1.0 0.3 4.0
0.5 -0.5 6.0
0.0 0.0 8.0
```

### 5.2 Verbose Example

```ply
ply
format ascii 1.0
comment ppf_version 1.0
comment plant_id ppf_example_begonia_maculata_001_t2
comment subject_id begonia_maculata_01
comment timepoint_index 2
comment species Begonia_maculata
comment acquisition_date 2025-01-22  ISO 8601 format
comment acquisition_time 13:46:05Z
comment sensor_type sfm
comment dataset_name PPF_Example_Dataset
comment processing_level cleaned
element vertex 15
property float x
property float y
property float z
property uchar red
property uchar green
property uchar blue
property int semantic_id
property int instance_id
end_header

0.0 0.0 0.0 139 69 19 2 
0.0 0.0 5.0 139 69 19 2
2.0 1.0 8.0 0 255 0 1 1
3.0 1.5 9.0 0 255 0 1 1
-2.0 -1.0 8.0 0 200 0 1
-3.0 -1.5 9.0 0 200 0 1
```

---

## 6. Reference Implementation

See the reference/ directory for Python implementation:

| File | Contents |
|------|----------|
| ppf_io.py | Read/write functions |
| ppf_dataset.py | Dataset loading |
| ppf_validate.py | Validation utilities |

---

## 7. Version History and Future Extensions

### 7.1 Version History

| Version | Release-Date | Changes |
|---------|------|---------|
| 1.0-draft | 2026-05-14 | Initial specification |


### 7.2 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## Appendix A: Quick Reference

### File Checklist

```
- format binary_little_endian 1.0
- comment ppf_version 1.0
- comment plant_id [unique_id]
- property float x/y/z
- Coordinates must match unified format: scaled in mm, Z-up, coordinate origin is median-centered

If annotated:
  - property int semantic_label
  - property int instance_id

If temporal:
  - comment subject_id
  - comment timepoint_index

If hierarchical:
  - property int organ_id
  - parent_class defined in schema

```

---

*PPF Specification v1.0 — Draft*
