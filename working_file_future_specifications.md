

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
      "type": "void"
      "parent_class": null
    },
    "1": {
      "name": "leaf",
      "type": "thing"
      "parent_class": 3,
      "hierarchy_level": 3
    },
    "2": {
      "name": "stem",
      "type": "stuff"
      "parent_class": null,
      "hierarchy_level": 1
    },
    "3": {
      "name": "petiole",
      "type": "thing"
      "parent_class": 2,
      "hierarchy_level": 2
    },
    "12": {
      "name": "leaflet",
      "type": "thing"
      "parent_class": 1,
      "hierarchy_level": 4
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