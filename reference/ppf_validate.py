"""
PPF Validation Module

Validate PPF-compliant files and datasets.

Requirements:
    pip install numpy plyfile
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from plyfile import PlyData


class ValidationResult:
    """Container for validation results."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
    
    @property
    def is_valid(self) -> bool:
        """True if no errors."""
        return len(self.errors) == 0
    
    def add_error(self, message: str) -> None:
        """Add an error (file is not PPF-compliant)."""
        self.errors.append(f"ERROR: {message}")
    
    def add_warning(self, message: str) -> None:
        """Add a warning (file works but has issues)."""
        self.warnings.append(f"WARNING: {message}")
    
    def add_info(self, message: str) -> None:
        """Add informational message."""
        self.info.append(f"INFO: {message}")
    
    def __str__(self) -> str:
        lines = []
        if self.errors:
            lines.extend(self.errors)
        if self.warnings:
            lines.extend(self.warnings)
        if self.info:
            lines.extend(self.info)
        
        if not lines:
            return "Valid PPF file"
        return '\n'.join(lines)


def validate_ppf_file(
    filepath: str,
    strict: bool = False,
    check_coordinates: bool = True
) -> ValidationResult:
    """
    Validate a PPF-compliant PLY file.
    
    Parameters
    ----------
    filepath : str
        Path to .ply file
    strict : bool
        If True, also check recommended fields
    check_coordinates : bool
        If True, verify coordinate conventions
        
    Returns
    -------
    ValidationResult
        Validation results with errors, warnings, and info
        
    Examples
    --------
    >>> result = validate_ppf_file("plant.ply")
    >>> if result.is_valid:
    ...     print("File is valid!")
    >>> else:
    ...     print(result)
    """
    result = ValidationResult()
    filepath = Path(filepath)
    
    # Check file exists
    if not filepath.exists():
        result.add_error(f"File not found: {filepath}")
        return result
    
    # Try to read PLY
    try:
        plydata = PlyData.read(str(filepath))
    except Exception as e:
        result.add_error(f"Failed to read PLY file: {e}")
        return result
    
    # Check for vertex element
    if 'vertex' not in plydata:
        result.add_error("Missing 'vertex' element")
        return result
    
    vertex = plydata['vertex']
    n_points = len(vertex.data)
    result.add_info(f"Point count: {n_points}")
    
    # Parse comments
    metadata = {}
    for comment in plydata.comments:
        parts = comment.split(' ', 1)
        if len(parts) == 2:
            metadata[parts[0]] = parts[1]
    
    # === MANDATORY CHECKS ===
    
    # Check ppf_version
    if 'ppf_version' not in metadata:
        result.add_error("Missing mandatory comment: ppf_version")
    else:
        result.add_info(f"PPF version: {metadata['ppf_version']}")
    
    # Check plant_id
    if 'plant_id' not in metadata:
        result.add_error("Missing mandatory comment: plant_id")
    else:
        result.add_info(f"Plant ID: {metadata['plant_id']}")
    
    # Check XYZ properties
    for prop in ['x', 'y', 'z']:
        if prop not in vertex.dtype.names:
            result.add_error(f"Missing mandatory property: {prop}")
    
    # === CONDITIONAL CHECKS ===
    
    # Temporal fields
    has_subject = 'subject_id' in metadata
    has_timepoint = 'timepoint_index' in metadata
    if has_subject != has_timepoint:
        result.add_error(
            "Temporal datasets require both 'subject_id' and 'timepoint_index'"
        )
    elif has_subject:
        result.add_info(f"Temporal: subject={metadata['subject_id']}, t={metadata['timepoint_index']}")
    
    # Label fields
    has_semantic = 'semantic_label' in vertex.dtype.names
    has_instance = 'instance_id' in vertex.dtype.names
    has_organ = 'organ_id' in vertex.dtype.names
    
    if has_instance and not has_semantic:
        result.add_error("'instance_id' requires 'semantic_label'")
    
    if has_organ and not has_instance:
        result.add_error("'organ_id' requires 'instance_id'")
    
    if has_semantic:
        labels = np.unique(vertex['semantic_label'])
        result.add_info(f"Semantic labels present: {labels.tolist()}")
    
    if has_instance:
        result.add_info("Instance IDs present")
    
    if has_organ:
        result.add_info("Hierarchical organ IDs present")
    
    # === COORDINATE CHECKS ===
    
    if check_coordinates and all(p in vertex.dtype.names for p in ['x', 'y', 'z']):
        xyz = np.column_stack([vertex['x'], vertex['y'], vertex['z']])
        
        # Check median-centered
        median = np.median(xyz, axis=0)
        if np.any(np.abs(median) > 50):  # More than 5cm from origin
            result.add_warning(
                f"Points not median-centered. Median: [{median[0]:.1f}, {median[1]:.1f}, {median[2]:.1f}] mm"
            )
        
        # Check reasonable scale (assuming mm)
        extent = xyz.max(axis=0) - xyz.min(axis=0)
        if np.any(extent > 10000):  # More than 10 meters
            result.add_warning(
                f"Large extent detected: [{extent[0]:.0f}, {extent[1]:.0f}, {extent[2]:.0f}] mm. "
                "Verify units are millimeters."
            )
        if np.any(extent < 1):  # Less than 1mm
            result.add_warning(
                f"Small extent detected: [{extent[0]:.2f}, {extent[1]:.2f}, {extent[2]:.2f}] mm. "
                "Verify units are millimeters."
            )
    
    # === STRICT MODE (recommended fields) ===
    
    if strict:
        recommended_comments = ['species', 'sensor_type', 'acquisition_date']
        for field in recommended_comments:
            if field not in metadata:
                result.add_warning(f"Recommended comment missing: {field}")
    
    return result


def validate_ppf_dataset(dataset_path: str) -> Dict[str, ValidationResult]:
    """
    Validate an entire PPF dataset.
    
    Parameters
    ----------
    dataset_path : str
        Path to dataset root directory
        
    Returns
    -------
    Dict[str, ValidationResult]
        Mapping from file/component names to validation results
        
    Examples
    --------
    >>> results = validate_ppf_dataset("my_dataset/")
    >>> for name, result in results.items():
    ...     if not result.is_valid:
    ...         print(f"{name}:")
    ...         print(result)
    """
    results = {}
    root = Path(dataset_path)
    
    # Validate dataset.json
    dataset_json = root / 'dataset.json'
    results['dataset.json'] = _validate_dataset_json(dataset_json)
    
    # Validate schema.json
    schema_json = root / 'schema.json'
    results['schema.json'] = _validate_schema_json(schema_json)
    
    # If dataset.json is valid, validate all plant files
    if results['dataset.json'].is_valid:
        with open(dataset_json) as f:
            index = json.load(f)
        
        for plant in index.get('plants', []):
            plant_file = plant.get('file', '')
            filepath = root / plant_file
            results[plant_file] = validate_ppf_file(str(filepath))
    
    # Validate splits
    splits_dir = root / 'splits'
    if splits_dir.exists():
        results['splits/'] = _validate_splits(splits_dir, root / 'dataset.json')
    
    return results


def _validate_dataset_json(filepath: Path) -> ValidationResult:
    """Validate dataset.json structure."""
    result = ValidationResult()
    
    if not filepath.exists():
        result.add_error("dataset.json not found")
        return result
    
    try:
        with open(filepath) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        result.add_error(f"Invalid JSON: {e}")
        return result
    
    # Required fields
    required = ['dataset_name', 'ppf_version', 'description', 'license', 'created', 'plants']
    for field in required:
        if field not in data:
            result.add_error(f"Missing required field: {field}")
    
    # Validate plants array
    plants = data.get('plants', [])
    if not isinstance(plants, list):
        result.add_error("'plants' must be an array")
    else:
        result.add_info(f"Plants listed: {len(plants)}")
        
        # Check each plant entry
        for i, plant in enumerate(plants):
            if 'file' not in plant:
                result.add_error(f"Plant {i}: missing 'file'")
            if 'plant_id' not in plant:
                result.add_error(f"Plant {i}: missing 'plant_id'")
    
    # Check coordinate system
    coord_sys = data.get('coordinate_system', {})
    if coord_sys.get('unit') != 'mm':
        result.add_warning("coordinate_system.unit should be 'mm'")
    if coord_sys.get('up_axis') != 'Z':
        result.add_warning("coordinate_system.up_axis should be 'Z'")
    if coord_sys.get('origin') != 'median_centered':
        result.add_warning("coordinate_system.origin should be 'median_centered'")
    
    return result


def _validate_schema_json(filepath: Path) -> ValidationResult:
    """Validate schema.json structure."""
    result = ValidationResult()
    
    if not filepath.exists():
        result.add_error("schema.json not found")
        return result
    
    try:
        with open(filepath) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        result.add_error(f"Invalid JSON: {e}")
        return result
    
    # Required fields
    if 'schema_version' not in data:
        result.add_error("Missing required field: schema_version")
    
    if 'labels' not in data:
        result.add_error("Missing required field: labels")
        return result
    
    labels = data['labels']
    if not isinstance(labels, dict):
        result.add_error("'labels' must be an object")
        return result
    
    result.add_info(f"Labels defined: {len(labels)}")
    
    # Check each label
    for label_id, label_def in labels.items():
        # Verify ID is numeric string
        try:
            int(label_id)
        except ValueError:
            result.add_error(f"Label ID must be integer string: {label_id}")
        
        # Required label fields
        if 'name' not in label_def:
            result.add_error(f"Label {label_id}: missing 'name'")
        if 'type' not in label_def:
            result.add_error(f"Label {label_id}: missing 'type'")
        elif label_def['type'] not in ['void', 'stuff', 'thing']:
            result.add_error(f"Label {label_id}: type must be void/stuff/thing")
        if 'color' not in label_def:
            result.add_error(f"Label {label_id}: missing 'color'")
        elif not isinstance(label_def['color'], list) or len(label_def['color']) != 3:
            result.add_error(f"Label {label_id}: color must be [R, G, B]")
    
    # Check label 0 exists
    if '0' not in labels:
        result.add_warning("Label 0 (unlabeled) not defined")
    
    return result


def _validate_splits(splits_dir: Path, dataset_json: Path) -> ValidationResult:
    """Validate split files."""
    result = ValidationResult()
    
    # Load valid subject IDs from dataset.json
    valid_subjects = set()
    try:
        with open(dataset_json) as f:
            data = json.load(f)
        for plant in data.get('plants', []):
            if 'subject_id' in plant:
                valid_subjects.add(plant['subject_id'])
    except:
        result.add_warning("Could not load dataset.json to verify subject IDs")
        return result
    
    # Check each split file
    all_split_subjects = set()
    for split_file in splits_dir.glob('*.txt'):
        with open(split_file) as f:
            subjects = [line.strip() for line in f if line.strip()]
        
        result.add_info(f"{split_file.name}: {len(subjects)} subjects")
        
        # Check for invalid subjects
        for subj in subjects:
            if valid_subjects and subj not in valid_subjects:
                result.add_error(f"{split_file.name}: unknown subject '{subj}'")
            
            if subj in all_split_subjects:
                result.add_error(f"{split_file.name}: subject '{subj}' appears in multiple splits")
            all_split_subjects.add(subj)
    
    # Check coverage
    if valid_subjects:
        missing = valid_subjects - all_split_subjects
        if missing:
            result.add_warning(f"Subjects not in any split: {missing}")
    
    return result


def print_validation_summary(results: Dict[str, ValidationResult]) -> None:
    """Print a formatted validation summary."""
    n_valid = sum(1 for r in results.values() if r.is_valid)
    n_total = len(results)
    
    print(f"\nValidation Summary: {n_valid}/{n_total} components valid\n")
    print("=" * 60)
    
    # Group by status
    errors = [(k, v) for k, v in results.items() if v.errors]
    warnings = [(k, v) for k, v in results.items() if v.warnings and not v.errors]
    valid = [(k, v) for k, v in results.items() if v.is_valid and not v.warnings]
    
    if errors:
        print("\n❌ ERRORS:")
        for name, result in errors:
            print(f"\n  {name}:")
            for msg in result.errors:
                print(f"    {msg}")
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for name, result in warnings:
            print(f"\n  {name}:")
            for msg in result.warnings:
                print(f"    {msg}")
    
    if valid:
        print("\n✅ VALID:")
        for name, _ in valid:
            print(f"  {name}")
    
    print("\n" + "=" * 60)