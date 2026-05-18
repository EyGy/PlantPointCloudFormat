# Plant Point Cloud Format (PPF) Specification

*Version 1.0 — Draft 0.3 planned for a first conference submission in June 2026*

**Status**: Pre-Submission-Draft — Open for community feedback

**Last Updated**: 2026-05-18 (YYYY-MM-DD)

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

The Plant Point Cloud Format (PPF) is a standardized format for representing individual plant point clouds, designed specifically for plant phenotyping, agricultural research, and machine learning applications. Its purpose is to address current challenges in plant point cloud research like inconsistent annotations, missing metadata and time wasted on format conversion. PPF defines a consistent file structure based on PLY with standardized label formats and flexible but structured metadata conventions. PPF is a free and non-commercial community project created by & for plant point cloud researchers with the goal of making all our lives easier through on a common standard. Feel invited to suggest improvements or to contribute directly (see [CONTRIBUTING.md](CONTRIBUTING.md)).

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
| PLY Compatibility | binary_big_endian | While little_endian is the preferred binary format,big_endian is allowed in PLY and thus supported by PPF to ensure compatibility 
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

#### 3.1.1 Mandatory PPF Header 

PPF files are based on PLY, so the standard PLY header lines are mandatory:

| Key | Type | Description | Example |
|-----|------|-------------|---------|
| ply | file-type | Every file needs to start with this to ensure PLY format compatibility | ply |
| format | encoding-type | Specifies encoding. use either: "ascii 1.0" or "binary_little_endian 1.0" ("binary_big_endian 1.0" is supported but not recommend) |binary_little_endian 1.0 |
| element vertex | indicator for number of points | Specifies the number of points provided in the document | element vertex 52134 |

Additionally PPF files have to include two mandatory comments:

| Key | Type | Description | Example |
|-----|------|-------------|---------|
| ppf_version | string | Specification version | ppf_version 1.0 |
| plant_id | string | Unique identifier for this scan | arabidopsis_001_t0 |


#### 3.1.2 Mandatory Vertex Properties

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

This is the minimal header for a legit PPF file. At this point we could just use PLY so the real value that PPF is adding comes with structured header comments to extend this minimal version.


### 3.2 Conditional Fields

#### 3.2.1 Annotation Vertex Property ( for annotated point clouds)

| Property | Data Type | Description |
|----------|-----------|-------------|
| semantic_id | int | Semantic class ID (see [Section 4](#4-label-schema-format)) |
| instance_id | int | Instance ID within semantic class |

Semantic IDs are required for instance IDs to work. Semantic IDs can be used without instance IDs.

**Instance ID conventions**:

| Value | Meaning |
|-------|---------|
| 0 | Unlabeled or "stuff" class (no instances) |
| 1, 2, 3, ... | Distinct instance IDs (see [Section 4](#4-label-schema-format)) |

***Important***: Instance IDs are unique **within each semantic class**, not globally. An instance_id = 0 indicates that this element has no instance label (valid instance labels start counting with 1).
When annotating plants we recommend counting the instances bottom-top. Thus, the lowest leaf (closest to emergence point) gets instance_id = 1 and the most upper leaf gets instance_id = max.

This may be very difficult for dense plants - in that case try to follow this recommendation to the best of your ability.



### 3.3 Recommended Fields (include additional information)

#### 3.3.1 Recommended Header Comments

| Key | Type | Description | Example |
|-----|------|-------------|---------|
| species | string | Scientific name (underscore-separated) | Arabidopsis_thaliana |
| acquisition_date | string | ISO 8601 format | 2024-03-15 |
| acquisition_time | string | ISO 8601 format | 13:46:05Z |
| sensor_type | string | Acquisition modality | See vocabulary below |
| plant_category | string | Grouping to identify structurally similar plants | See vocabulary below |
| dataset_name | string | Parent dataset identifier | BonnBeetClouds |
|other | |This list can be arbitrarily extended based on the available metadata of your dataset | Timepoint inexing, organ hiearchy, etc.

**Plant category vocabulary**:

The suggested below distinction is a purley structural distinction for the AI/ML benchmark datasets that will follow upon the release of PPF.
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
| other | If you use other sensors, please contribute by extending this list!|

#### 3.3.2 Additional Point/Vertex Properties

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

#### 3.4.1 Optional Header Comments

| Key | Type | Description | Example |
|-----|------|-------------|---------|
| growth_stage | string | BBCH code or DAE (Days after emergence) | BBCH_14, DAE_21 |
| cultivar | string | Cultivar/genotype | Col-0 |
| treatment | string | Experimental treatment | drought_stress |
| processing_level | string | Processing stage | raw, cleaned |
| source_file | string | Original filename | scan_001.las |
| other | Other/unspecified | |

#### 3.4.2 Optional Point/Vertex Properties

| Property | Data Type | Description |
|----------|-----------|-------------|
| nx | float | Normal X component |
| ny | float | Normal Y component |
| nz | float | Normal Z component |
| confidence | float | Prediction confidence (0.0-1.0) |

---

## 4. Label Schema Format


### 4.1 Recommended Base Schema

Use the following IDs for common classes to maximize interoperability. The IDs can be arbitrarily extended with new custom classes as needed 
(e.g.: "class" leaflet with ID=11 or class "closed_bud" with ID=24). Avoid double usage of already listed IDs for another class (even if the listed class is not present in your dataset).

| ID | Name | Type | PO Term | PO ID |Explanation |
|----|------|------|------|------|----|
| 0 | unlabeled | void ||||
| 1 | leaf | thing |vascular leaf|PO:0009025||
| 2 | stem | thing |stem|PO:0009047| For single-stem plants this could also be type "stuff"|
| 3 | petiole | thing |petiole|PO:0020038||
| 4 | branch | thing |branch|PO:0025073||
| 5 | flower | thing |flower|PO:0009046||
| 6 | fruit | thing |fruit|PO:0009001||
| 7 | root | thing |root system|PO:0009005||
| 8 | substrate | stuff ||| Soil, coco, or other growth medium|
| 9 | pot | stuff |||Container/box containing the substrate|
---

***Important:*** If your data uses a different label encoding, it must be defined in the PLY header as proposed in [section 4.2](#42-custom-label-encoding-schema).

***Biological Reference:*** Where applicable, labels are mapped to terms from the [Plant Ontology (PO; Jaiswal et al., 2005)](https://onlinelibrary.wiley.com/doi/10.1002/cfg.496). These mappings are informational — PPF tools are not required to interpret or store PO identifiers. Non-plant structures (substrate, pot) have no PO mapping.

### 4.2 Custom Label Encoding Schema
Custom labels are defined directly in the PLY header. E.g. if you want to distinguish between different kind of leaves within one plant this could look like this:

```ply
comment label 0 unlabeled void       
comment label 10 damaged_leaf thing
comment label 11 old_leaf thing
comment label 12 emerging_leaf thing
```
*Note:* Since the specification of ```comment label 0 unlabeled void``` is identical to PPF base schema it could also be left out in this example. For not specified labels the base schema is applied automatically.

***Important:*** If no label schema is defined, the data will be interpreted according to the recommended base schema presented in [section 4.1](#41-recommended-base-schema). If you use custom labels it is highly recommended not override label IDs used in the base schema. While this is possible and supported by the PPF dataloader, it can lead to confusion and inconsistencies later on or when other researchers want to use your work.


## 5. Examples

See the examples/ directory for complete example files:

| Example | Description |
|---------|-------------|
| minimal_example.ply | Simplest valid PPF file |
| full_example.ply | Verbose PPF example |

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
comment plant_id ppf_example_plant_001_t2
comment subject_id begonia_maculata_01
comment timepoint_index 2
comment species Begonia_maculata
comment acquisition_date 2025-01-22
comment acquisition_time 13:46:05Z
comment sensor_type sfm
comment dataset_name PPF_Example_Dataset
comment processing_level cleaned
comment label 10 damaged_leaf thing
element vertex 15123
property float x
property float y
property float z
property uchar red
property uchar green
property uchar blue
property int semantic_id
property int instance_id
end_header

0.0 0.0 0.0 139 69 19 2 1
0.0 0.0 5.0 139 69 19 2 1
2.0 1.0 8.0 0 255 0 10 1
3.0 1.5 9.0 0 255 0 10 1
-2.0 -1.0 8.0 0 200 0 7 0
-3.0 -1.5 9.0 0 200 0 7 0
...more points follow...
```

---

## 6. Reference Implementation

See the reference/ directory for Python implementation:

| File | Contents |
|------|----------|
| ppf.py | PPF class definition and hardcoded global variables (e.g. label base schema) |
| io.py | Read/write functions |
| validate.py | Validation utilities |

---

## 7. Version History and Future Extensions

### 7.1 Version History

| Version | Release-Date | Changes |
|---------|------|---------|
| 1.0-draft | 2026-05-14 | Initial specification |


### 7.2 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## Appendix A: Quick Checklist

### File Checklist - is your file ready for PPF?

- Is your plant point cloud
  - Coordinates scaled in mm
  - Oriented with Z-axis up
  - Coordinate origin median-centered
- Does the file header comply with PLY standards?

- Does it contain additional information as PLY comments?
  - comment ppf_version 1.0
  - comment plant_id [unique_id]
  - additional metadata as comments

- Are annotations encoded as per point vlaues?
  - property int semantic_id
  - property int instance_id

---

*PPF Specification v1.0 — Draft*
