# Plant Point Cloud Format (PPF) Specification

**Version 1.0 — Draft 0.1**

**Status**: Draft — Open for community feedback

**Last Updated**: 2026-03-03 (YYYY-MM-DD)

---

## Table of Contents

1. [Introduction and Motivation](#1-introduction-and-motivation)
2. [File Format Overview](#2-file-format-overview)
3. [PLY Header Specification](#3-ply-header-specification)
   - [3.1 Mandatory Fields](#31-mandatory-fields)
   - [3.2 Conditional Fields](#32-conditional-fields)
   - [3.3 Recommended Fields](#33-recommended-fields)
   - [3.4 Optional Extensions](#34-optional-extensions)
4. [Label Schema Format](#4-label-schema-format)
5. [Hierarchical Instance Labeling](#5-hierarchical-instance-labeling)
6. [Dataset Organization](#6-dataset-organization)
   - [6.1 Directory Structure](#61-directory-structure)
   - [6.2 Dataset Index File](#62-dataset-index-file)
   - [6.3 Train Val Test Splits](#63-train-val-test-splits)
7. [Temporal Datasets](#7-temporal-datasets)
8. [Examples](#8-examples)
9. [Reference Implementation](#9-reference-implementation)
10. [Version History and Future Extensions](#10-version-history-and-future-extensions)

---

## 1. Introduction and Motivation

### 1.1 Purpose

The Plant Point Cloud Format (PPF) is a standardized format for representing individual plant point clouds, designed specifically for plant phenotyping, agricultural research, and machine learning applications.

### 1.2 Scope

**In scope (v1.0)**:
- Individual plant point clouds (one plant per file)
- Semantic and instance segmentation labels
- Hierarchical organ relationships
- Spatio-temporal (time-series) datasets
- Dataset organization and metadata

**Out of scope (v1.0)**:
- Multi-plant scene representations
- Mesh data
- Multi-spectral data (noted for future extension)
- Raw sensor data formats

---

## 2. File Format Overview

### 2.1 Base Format: PLY

PPF uses the **Polygon File Format (PLY)** as its base.
PLY files are supported by Open3D, trimesh, plyfile, CloudCompare, MeshLab, and many more.


### 2.2 Encoding

| Context | Encoding | Rationale |
|---------|----------|-----------|
| Production | binary_little_endian | Compact, fast |
| Debugging | ascii | Human-readable |

**Requirement**: PPF-compliant tools MUST support both encodings.

**Recommendation for new datasets**: Distribute in binary with 1-2 ASCII examples.

### 2.3 Coordinate System Conventions

**All PPF point clouds MUST use these conventions:**

| Property | Convention | Notes |
|----------|------------|-------|
| **Unit** | Millimeters (mm) | All XYZ coordinates |
| **Up axis** | Z-positive | Z increases upward |
| **Origin** | Median-centered | Origin at median(X), median(Y), median(Z) |

#### Why Median-Centered Origin?

- Computable without labels (works for unlabeled data)
- Robust to outliers
- Normalizes spatial distribution across plant architectures


### 2.4 One Plant Per File

Each PPF file represents **exactly one individual plant**.

Multi-plant scenes must be segmented into individual files.

---

## 3. PLY Header Specification

PPF extends PLY headers with structured comments:

```
comment key value
```

Where key is a single token and value is the remainder of the line.

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

Required when specific conditions apply.

#### 3.2.1 Annotation Fields

**Required if**: Point cloud contains annotations.

| Property | Data Type | Description |
|----------|-----------|-------------|
| semantic_label | int | Semantic class ID (see Section 4) |
| instance_id | int | Instance ID within semantic class |

**Instance ID conventions**:

| Value | Meaning |
|-------|---------|
| 0 | Unlabeled or "stuff" class (no instances) |
| 1, 2, 3, ... | Distinct instance IDs |

**Important**: Instance IDs are unique **within each semantic class**, not globally.

#### 3.2.2 Temporal Dataset Fields

**Required if**: Plant is part of a temporal (time-series) dataset.

| Key | Type | Description | Example |
|-----|------|-------------|---------|
| subject_id | string | Persistent ID across timepoints | plant_001 |
| timepoint_index | integer | Zero-indexed temporal ordering | 0, 1, 2 |


### 3.3 Recommended Fields

Include when information is available.

#### 3.3.1 Header Comments

| Key | Type | Description | Example |
|-----|------|-------------|---------|
| species | string | Scientific name (underscore-separated) | Arabidopsis_thaliana |
| acquisition_date | string | ISO 8601 format | 2024-03-15 |
| sensor_type | string | Acquisition modality | See vocabulary below |
| dataset_name | string | Parent dataset identifier | BonnBeetClouds |

**Sensor type vocabulary**:

| Value | Description |
|-------|-------------|
| lidar_terrestrial | Terrestrial laser scanning |
| lidar_mobile | Mobile/handheld LiDAR |
| sfm | Structure from Motion |
| structured_light | Structured light scanning |
| tof | Time-of-flight camera |
| rgb_d | RGB-D sensor |
| other | Other/unspecified |

#### 3.3.2 Vertex Properties

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

#### 3.4.2 Vertex Properties

| Property | Data Type | Description |
|----------|-----------|-------------|
| nx | float | Normal X component |
| ny | float | Normal Y component |
| nz | float | Normal Z component |
| confidence | float | Prediction confidence (0.0-1.0) |
| organ_id | int | Hierarchical grouping (see Section 5) |

---

## 4. Label Schema Format

Each dataset MUST include a schema.json file.

### 4.1 Schema Structure

```json
{
  "schema_version": "1.0",
  "description": "Label schema for [dataset name]",
  "labels": {
    "0": {
      "name": "unlabeled",
      "type": "void",
      "description": "Unlabeled or unknown points",
      "color": [128, 128, 128]
    },
    "1": {
      "name": "leaf",
      "type": "thing",
      "description": "Leaf blade tissue",
      "color": [0, 255, 0]
    }
  }
}
```

### 4.2 Field Definitions

#### Top-Level Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| schema_version | Yes | string | Schema format version |
| description | No | string | Human-readable description |
| labels | Yes | object | Label definitions keyed by ID |

#### Label Object Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| name | Yes | string | Short identifier (snake_case) |
| type | Yes | string | void, thing, or stuff |
| description | No | string | Human-readable description |
| color | Yes | array | RGB values [R, G, B] |
| parent_class | No | integer | Parent class for hierarchy |

### 4.3 Label Types

| Type | Has Instances | Description | Examples |
|------|---------------|-------------|----------|
| void | No | Ignored in evaluation | unlabeled, noise |
| stuff | No | Amorphous regions | soil, background |
| thing | Yes | Countable objects | leaf, flower, fruit |

### 4.4 Reserved Label IDs

| ID | Reserved For |
|----|--------------|
| 0 | unlabeled / void |
| 255 | Future use |

Labels 1-254 available for dataset-specific classes.

### 4.5 Recommended Base Schema

Use these IDs for common classes to maximize interoperability:

| ID | Name | Type | Color RGB |
|----|------|------|-----------|
| 0 | unlabeled | void | [128, 128, 128] |
| 1 | leaf | thing | [0, 255, 0] |
| 2 | stem | thing | [139, 69, 19] |
| 3 | petiole | thing | [0, 128, 0] |
| 4 | flower | thing | [255, 255, 0] |
| 5 | fruit | thing | [255, 0, 0] |
| 6 | root | thing | [128, 64, 0] |
| 7 | medium | stuff | [64, 32, 0] |
| 8 | pot | stuff | [192, 192, 192] |

Datasets with additional classes SHOULD use IDs >= 10.

---

## 5. Hierarchical Instance Labeling (optional extension)

### 5.1 Motivation

Many plants have hierarchical organ structures:

```
Plant
├── Main Stem
│   ├── Branch 1
│   │   ├── Leaf 1 (compound)
│   │   │   ├── Leaflet 1a
│   │   │   ├── Leaflet 1b
│   │   │   └── Leaflet 1c
│   │   └── Flower Cluster 1
│   │       ├── Flower 1
│   │       └── Flower 2
│   └── Branch 2
│       └── ...
```

Standard instance labels (Section 3.2.2) capture individual instances but not relationships. Hierarchical labeling enables:

- Part-whole relationship modeling
- Multi-scale analysis
- Developmental tracking

### 5.2 Enabling Hierarchical Labels

#### 5.2.1 Additional Vertex Property

Add the optional organ_id property:

| Property | Data Type | Description |
|----------|-----------|-------------|
| organ_id | int | Parent structure ID |

#### 5.2.2 Schema Extension

Define parent-child relationships in schema.json:

```json
{
  "schema_version": "1.0",
  "labels": {
    "0": {
      "name": "unlabeled",
      "type": "void",
      "color": [128, 128, 128],
      "parent_class": null
    },
    "1": {
      "name": "leaflet",
      "type": "thing",
      "color": [144, 238, 144],
      "parent_class": 2,
      "hierarchy_level": 0
    },
    "2": {
      "name": "leaf",
      "type": "thing",
      "color": [0, 255, 0],
      "parent_class": 3,
      "hierarchy_level": 1
    },
    "3": {
      "name": "branch",
      "type": "thing",
      "color": [139, 90, 43],
      "parent_class": 4,
      "hierarchy_level": 2
    },
    "4": {
      "name": "main_stem",
      "type": "stuff",
      "color": [139, 69, 19],
      "parent_class": null,
      "hierarchy_level": 3
    }
  }
}
```

### 5.3 How It Works

#### 5.3.1 Data Structure

Each point has three label properties:

| Property | Purpose |
|----------|---------|
| semantic_label | What class is this point? |
| instance_id | Which instance of that class? |
| organ_id | Which parent structure does it belong to? |

#### 5.3.2 Example: Compound Leaf

Consider a compound tomato leaf with 3 leaflets:

| Point | semantic_label | instance_id | organ_id | Interpretation |
|-------|----------------|-------------|----------|----------------|
| A | 1 (leaflet) | 1 | 100 | Leaflet #1, part of leaf #100 |
| B | 1 (leaflet) | 1 | 100 | Leaflet #1, part of leaf #100 |
| C | 1 (leaflet) | 2 | 100 | Leaflet #2, part of leaf #100 |
| D | 1 (leaflet) | 3 | 100 | Leaflet #3, part of leaf #100 |
| E | 2 (leaf) | 100 | 500 | Leaf #100, part of branch #500 |
| F | 3 (branch) | 500 | 0 | Branch #500 (top-level, no parent) |

**Key rules**:
- organ_id = 0 means no parent (top-level structure)
- organ_id values reference instance_id values of the parent class
- The parent class is defined in the schema via parent_class

#### 5.3.3 Reconstructing Hierarchy

```python
def build_hierarchy(cloud, schema):
    """Reconstruct organ hierarchy from flat labels."""
    
    hierarchy = {}
    
    # Group points by (semantic_label, instance_id)
    instances = defaultdict(list)
    for i, (sem, inst, org) in enumerate(zip(
        cloud.semantic_labels,
        cloud.instance_ids,
        cloud.organ_ids
    )):
        instances[(sem, inst)].append({
            'point_idx': i,
            'organ_id': org
        })
    
    # Build tree structure
    for (sem_label, inst_id), points in instances.items():
        label_info = schema['labels'][str(sem_label)]
        parent_class = label_info.get('parent_class')
        organ_id = points[0]['organ_id']  # All points share same organ_id
        
        hierarchy[(sem_label, inst_id)] = {
            'name': label_info['name'],
            'instance_id': inst_id,
            'parent': (parent_class, organ_id) if parent_class and organ_id else None,
            'point_indices': [p['point_idx'] for p in points]
        }
    
    return hierarchy
```

### 5.4 Best Practices

#### 5.4.1 When to Use Hierarchical Labels

**Use when**:
- Modeling compound leaves (leaflets -> leaf)
- Tracking branching structures
- Multi-scale phenotyping
- Developmental studies

**Skip when**:
- Simple plants without clear hierarchy
- Annotation budget is limited
- Downstream task does not need part-whole relationships

#### 5.4.2 Annotation Guidelines

1. **Bottom-up annotation**: Label finest-grain structures first, then group
2. **Consistent granularity**: Do not mix hierarchical and flat labels for same organ type
3. **Document conventions**: Note dataset-specific hierarchy decisions in README

#### 5.4.3 Backward Compatibility

Files with hierarchical labels remain compatible with non-hierarchical tools:
- semantic_label and instance_id work independently
- organ_id is simply ignored if not needed
- Can flatten hierarchy by ignoring organ_id

---

## 6. Dataset Organization

### 6.1 Directory Structure

```
dataset_name/
├── dataset.json              # Dataset metadata and index
├── schema.json               # Label definitions
├── README.md                 # Dataset documentation
├── plants/                   # Point cloud files
│   ├── plant_001_t0.ply
│   ├── plant_001_t1.ply
│   └── ...
├── splits/                   # Train/val/test splits
│   ├── train.txt
│   ├── val.txt
│   └── test.txt
└── examples/                 # ASCII examples (optional)
    └── example_plant.ply
```

### 6.2 Dataset Index File

The dataset.json provides metadata and file index.

#### 6.2.1 Structure

```json
{
  "dataset_name": "Example_Dataset",
  "ppf_version": "1.0",
  "description": "Description of the dataset",
  "license": "CC-BY-4.0",
  "citation": "Author et al. (2024). Title. Journal.",
  "url": "https://example.org/dataset",
  "created": "2024-03-15",
  "coordinate_system": {
    "unit": "mm",
    "up_axis": "Z",
    "origin": "median_centered"
  },
  "statistics": {
    "n_plants": 100,
    "n_scans": 300,
    "n_subjects": 100,
    "n_timepoints_max": 5,
    "species": ["Zea_mays"],
    "sensor_types": ["lidar_terrestrial"]
  },
  "plants": [
    {
      "file": "plants/plant_001_t0.ply",
      "plant_id": "plant_001_t0",
      "subject_id": "plant_001",
      "timepoint_index": 0,
      "species": "Zea_mays",
      "sensor_type": "lidar_terrestrial",
      "acquisition_date": "2024-03-15",
      "n_points": 152847,
      "has_labels": true,
      "has_instances": true,
      "has_hierarchy": false
    }
  ]
}
```

#### 6.2.2 Top-Level Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| dataset_name | Yes | string | Unique dataset identifier |
| ppf_version | Yes | string | PPF specification version |
| description | Yes | string | Brief description |
| license | Yes | string | SPDX license identifier |
| citation | No | string | How to cite |
| url | No | string | Homepage or DOI |
| created | Yes | string | Creation date (ISO 8601) |
| coordinate_system | Yes | object | Coordinate conventions |
| statistics | No | object | Summary statistics |
| plants | Yes | array | Plant file entries |

#### 6.2.3 Plant Entry Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| file | Yes | string | Relative path to PLY |
| plant_id | Yes | string | Unique scan identifier |
| subject_id | Temporal | string | Physical plant ID |
| timepoint_index | Temporal | integer | Temporal index |
| species | No | string | Scientific name |
| sensor_type | No | string | Acquisition modality |
| acquisition_date | No | string | ISO 8601 date |
| n_points | No | integer | Point count |
| has_labels | No | boolean | Has semantic labels |
| has_instances | No | boolean | Has instance IDs |
| has_hierarchy | No | boolean | Has organ_id hierarchy |

### 6.3 Train Val Test Splits

#### 6.3.1 Format

Plain text files with one **subject ID** per line:

**splits/train.txt**:
```
plant_001
plant_002
plant_003
```

**splits/test.txt**:
```
plant_004
plant_005
```

#### 6.3.2 Critical: Split by Subject

Splits use subject_id (not plant_id) to prevent data leakage.

```python

# Load split

with open('splits/train.txt') as f:
    train_subjects = set(line.strip() for line in f)

# Get all training files (all timepoints of training subjects)

train_plants = [
    p for p in dataset['plants']
    if p['subject_id'] in train_subjects
]
```

#### 6.3.3 Split Principles

1. **Subject-based**: Split by physical plant
2. **No leakage**: All timepoints stay in same split
3. **Stratified**: Consider balancing by species/treatment
4. **Documented**: Record random seed and method

---

## 7. Temporal Datasets

### 7.1 Overview

Temporal datasets track plants across multiple timepoints. Proper handling prevents data leakage in ML experiments.

### 7.2 Identifier Conventions

| Identifier | Scope | Example | Purpose |
|------------|-------|---------|---------|
| plant_id | Per file | maize_001_t3 | Identify scan |
| subject_id | Across time | maize_001 | Track plant |
| timepoint_index | Per subject | 0, 1, 2 | Order timepoints |

### 7.3 Naming Convention

Recommended filename format:

```
{species}_{subject_number}_t{timepoint_index}.ply
```

Examples:
- arabidopsis_001_t0.ply
- arabidopsis_001_t1.ply
- tomato_042_t0.ply

### 7.4 Temporal Metadata

Include in dataset.json:

```json
{
  "temporal_info": {
    "is_temporal": true,
    "n_subjects": 50,
    "timepoints": [
      {"index": 0, "description": "DAE 7"},
      {"index": 1, "description": "DAE 14"},
      {"index": 2, "description": "DAE 21"}
    ]
  }
}
```

### 7.5 Preventing Data Leakage

**Critical**: Always split by subject_id.

**Wrong**:
```python

# Causes leakage!

all_plant_ids = [p['plant_id'] for p in plants]
train, test = train_test_split(all_plant_ids)
```

**Correct**:
```python
all_subject_ids = list(set(p['subject_id'] for p in plants))
train_subjects, test_subjects = train_test_split(all_subject_ids)
```

---

## 8. Examples

See the examples/ directory for complete example files:

| Example | Description |
|---------|-------------|
| minimal_example.ply | Simplest valid PPF file |
| full_example.ply | All features demonstrated |
| temporal_example/ | Complete temporal dataset |
| hierarchical_example/ | Hierarchical labeling |

### 8.1 Minimal Example

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

### 8.2 Full-Featured Example

```ply
ply
format ascii 1.0
comment ppf_version 1.0
comment plant_id arabidopsis_042_t2
comment subject_id arabidopsis_042
comment timepoint_index 2
comment species Arabidopsis_thaliana
comment sensor_type structured_light
comment acquisition_date 2024-03-15
comment dataset_name Example_Dataset
element vertex 6
property float x
property float y
property float z
property uchar red
property uchar green
property uchar blue
property int semantic_label
property int instance_id
end_header
0.0 0.0 0.0 139 69 19 2 0
0.0 0.0 5.0 139 69 19 2 0
2.0 1.0 8.0 0 255 0 1 1
3.0 1.5 9.0 0 255 0 1 1
-2.0 -1.0 8.0 0 200 0 1 2
-3.0 -1.5 9.0 0 200 0 1 2
```

---

## 9. Reference Implementation

See the reference/ directory for Python implementation:

| File | Contents |
|------|----------|
| ppf_io.py | Read/write functions |
| ppf_dataset.py | Dataset loading |
| ppf_validate.py | Validation utilities |

---

## 10. Version History and Future Extensions

### 10.1 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0-draft | [DATE] | Initial specification |

### 10.2 Planned Extensions

#### Multi-Spectral Support

```ply
property float band_850nm
property float band_680nm
property float ndvi
```

#### Mesh Support

```ply
element face 10000
property list uchar int vertex_indices
```


### 10.3 Contributing

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

If temporal:
  - comment subject_id
  - comment timepoint_index

If annotated:
  - property int semantic_label
  - property int instance_id

If hierarchical:
  - property int organ_id
  - parent_class defined in schema

```

### Dataset Checklist

```
- dataset.json
- schema.json
- plants/*.ply
- splits/train.txt, val.txt, test.txt
- Splits by subject_id

```

---

*PPF Specification v1.0 — Draft*