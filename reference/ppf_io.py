"""
PPF I/O Module

Read and write PPF-compliant PLY files.

Requirements:
    pip install numpy plyfile
"""

import numpy as np
from plyfile import PlyData, PlyElement
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class PPFPointCloud:
    """
    Container for a PPF point cloud.
    
    Attributes
    ----------
    xyz : np.ndarray
        Point coordinates, shape (N, 3), float32, in mm
    ppf_version : str
        PPF specification version
    plant_id : str
        Unique identifier for this scan
    subject_id : str, optional
        Persistent ID for physical plant (temporal datasets)
    timepoint_index : int, optional
        Temporal ordering index (temporal datasets)
    semantic_labels : np.ndarray, optional
        Semantic class IDs, shape (N,), int32
    instance_ids : np.ndarray, optional
        Instance IDs within each class, shape (N,), int32
    organ_ids : np.ndarray, optional
        Hierarchical parent IDs, shape (N,), int32
    rgb : np.ndarray, optional
        RGB colors, shape (N, 3), uint8
    intensity : np.ndarray, optional
        Intensity/reflectance values, shape (N,), float32
    normals : np.ndarray, optional
        Normal vectors, shape (N, 3), float32
    confidence : np.ndarray, optional
        Prediction confidence, shape (N,), float32
    metadata : dict
        Additional metadata from PLY comments
    """
    
    # Mandatory
    xyz: np.ndarray
    ppf_version: str
    plant_id: str
    
    # Conditional - temporal
    subject_id: Optional[str] = None
    timepoint_index: Optional[int] = None
    
    # Conditional - annotations
    semantic_labels: Optional[np.ndarray] = None
    instance_ids: Optional[np.ndarray] = None
    
    # Optional - hierarchy
    organ_ids: Optional[np.ndarray] = None
    
    # Optional - appearance
    rgb: Optional[np.ndarray] = None
    intensity: Optional[np.ndarray] = None
    
    # Optional - geometry
    normals: Optional[np.ndarray] = None
    
    # Optional - predictions
    confidence: Optional[np.ndarray] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def n_points(self) -> int:
        """Number of points in the cloud."""
        return len(self.xyz)
    
    @property
    def has_labels(self) -> bool:
        """Whether semantic labels are present."""
        return self.semantic_labels is not None
    
    @property
    def has_instances(self) -> bool:
        """Whether instance IDs are present."""
        return self.instance_ids is not None
    
    @property
    def has_hierarchy(self) -> bool:
        """Whether hierarchical organ IDs are present."""
        return self.organ_ids is not None
    
    @property
    def has_rgb(self) -> bool:
        """Whether RGB colors are present."""
        return self.rgb is not None
    
    @property
    def is_temporal(self) -> bool:
        """Whether this is part of a temporal dataset."""
        return self.subject_id is not None and self.timepoint_index is not None
    
    def get_instances(self, semantic_label: int) -> np.ndarray:
        """
        Get unique instance IDs for a semantic class.
        
        Parameters
        ----------
        semantic_label : int
            Semantic class ID
            
        Returns
        -------
        np.ndarray
            Array of unique instance IDs (excluding 0)
        """
        if not self.has_labels or not self.has_instances:
            return np.array([], dtype=np.int32)
        
        mask = self.semantic_labels == semantic_label
        instances = np.unique(self.instance_ids[mask])
        return instances[instances != 0]  # Exclude unlabeled/stuff
    
    def get_instance_mask(self, semantic_label: int, instance_id: int) -> np.ndarray:
        """
        Get boolean mask for a specific instance.
        
        Parameters
        ----------
        semantic_label : int
            Semantic class ID
        instance_id : int
            Instance ID within the class
            
        Returns
        -------
        np.ndarray
            Boolean mask, shape (N,)
        """
        if not self.has_labels or not self.has_instances:
            return np.zeros(self.n_points, dtype=bool)
        
        return (self.semantic_labels == semantic_label) & (self.instance_ids == instance_id)


def read_ppf(filepath: str) -> PPFPointCloud:
    """
    Read a PPF-compliant PLY file.
    
    Parameters
    ----------
    filepath : str
        Path to .ply file
        
    Returns
    -------
    PPFPointCloud
        Loaded point cloud with metadata
        
    Raises
    ------
    ValueError
        If file is not PPF-compliant (missing mandatory fields)
    FileNotFoundError
        If file does not exist
        
    Examples
    --------
    >>> cloud = read_ppf("plant_001.ply")
    >>> print(f"Loaded {cloud.n_points} points")
    >>> if cloud.has_labels:
    ...     print(f"Labels: {np.unique(cloud.semantic_labels)}")
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    plydata = PlyData.read(str(filepath))
    vertex = plydata['vertex']
    
    # Parse comments into metadata
    metadata = {}
    for comment in plydata.comments:
        parts = comment.split(' ', 1)
        if len(parts) == 2:
            key, value = parts
            # Try to parse as int
            try:
                value = int(value)
            except ValueError:
                # Try to parse as float
                try:
                    value = float(value)
                except ValueError:
                    pass  # Keep as string
            metadata[key] = value
    
    # Validate mandatory fields
    if 'ppf_version' not in metadata:
        raise ValueError(f"Missing mandatory comment 'ppf_version' in {filepath}")
    if 'plant_id' not in metadata:
        raise ValueError(f"Missing mandatory comment 'plant_id' in {filepath}")
    
    for prop in ['x', 'y', 'z']:
        if prop not in vertex.dtype.names:
            raise ValueError(f"Missing mandatory property '{prop}' in {filepath}")
    
    # Extract coordinates
    xyz = np.column_stack([
        vertex['x'],
        vertex['y'],
        vertex['z']
    ]).astype(np.float32)
    
    # Extract optional properties
    def get_property(name, dtype):
        if name in vertex.dtype.names:
            return np.array(vertex[name], dtype=dtype)
        return None
    
    # RGB
    rgb = None
    if all(p in vertex.dtype.names for p in ['red', 'green', 'blue']):
        rgb = np.column_stack([
            vertex['red'],
            vertex['green'],
            vertex['blue']
        ]).astype(np.uint8)
    
    # Normals
    normals = None
    if all(p in vertex.dtype.names for p in ['nx', 'ny', 'nz']):
        normals = np.column_stack([
            vertex['nx'],
            vertex['ny'],
            vertex['nz']
        ]).astype(np.float32)
    
    # Build point cloud object
    return PPFPointCloud(
        xyz=xyz,
        ppf_version=str(metadata.pop('ppf_version')),
        plant_id=str(metadata.pop('plant_id')),
        subject_id=str(metadata.pop('subject_id')) if 'subject_id' in metadata else None,
        timepoint_index=metadata.pop('timepoint_index', None),
        semantic_labels=get_property('semantic_label', np.int32),
        instance_ids=get_property('instance_id', np.int32),
        organ_ids=get_property('organ_id', np.int32),
        rgb=rgb,
        intensity=get_property('intensity', np.float32),
        normals=normals,
        confidence=get_property('confidence', np.float32),
        metadata=metadata
    )


def write_ppf(
    filepath: str,
    cloud: PPFPointCloud,
    binary: bool = True
) -> None:
    """
    Write a PPF-compliant PLY file.
    
    Parameters
    ----------
    filepath : str
        Output file path
    cloud : PPFPointCloud
        Point cloud to write
    binary : bool, default True
        Use binary encoding (recommended for production)
        
    Examples
    --------
    >>> cloud = PPFPointCloud(
    ...     xyz=np.random.randn(1000, 3).astype(np.float32),
    ...     ppf_version="1.0",
    ...     plant_id="my_plant_001"
    ... )
    >>> write_ppf("output.ply", cloud)
    """
    # Build vertex dtype
    dtype_list = [
        ('x', 'f4'),
        ('y', 'f4'),
        ('z', 'f4'),
    ]
    
    if cloud.rgb is not None:
        dtype_list.extend([
            ('red', 'u1'),
            ('green', 'u1'),
            ('blue', 'u1'),
        ])
    
    if cloud.intensity is not None:
        dtype_list.append(('intensity', 'f4'))
    
    if cloud.normals is not None:
        dtype_list.extend([
            ('nx', 'f4'),
            ('ny', 'f4'),
            ('nz', 'f4'),
        ])
    
    if cloud.semantic_labels is not None:
        dtype_list.append(('semantic_label', 'i4'))
    
    if cloud.instance_ids is not None:
        dtype_list.append(('instance_id', 'i4'))
    
    if cloud.organ_ids is not None:
        dtype_list.append(('organ_id', 'i4'))
    
    if cloud.confidence is not None:
        dtype_list.append(('confidence', 'f4'))
    
    # Create structured array
    vertex_data = np.empty(cloud.n_points, dtype=dtype_list)
    vertex_data['x'] = cloud.xyz[:, 0]
    vertex_data['y'] = cloud.xyz[:, 1]
    vertex_data['z'] = cloud.xyz[:, 2]
    
    if cloud.rgb is not None:
        vertex_data['red'] = cloud.rgb[:, 0]
        vertex_data['green'] = cloud.rgb[:, 1]
        vertex_data['blue'] = cloud.rgb[:, 2]
    
    if cloud.intensity is not None:
        vertex_data['intensity'] = cloud.intensity
    
    if cloud.normals is not None:
        vertex_data['nx'] = cloud.normals[:, 0]
        vertex_data['ny'] = cloud.normals[:, 1]
        vertex_data['nz'] = cloud.normals[:, 2]
    
    if cloud.semantic_labels is not None:
        vertex_data['semantic_label'] = cloud.semantic_labels
    
    if cloud.instance_ids is not None:
        vertex_data['instance_id'] = cloud.instance_ids
    
    if cloud.organ_ids is not None:
        vertex_data['organ_id'] = cloud.organ_ids
    
    if cloud.confidence is not None:
        vertex_data['confidence'] = cloud.confidence
    
    # Build comments
    comments = [
        f"ppf_version {cloud.ppf_version}",
        f"plant_id {cloud.plant_id}",
    ]
    
    if cloud.subject_id is not None:
        comments.append(f"subject_id {cloud.subject_id}")
    
    if cloud.timepoint_index is not None:
        comments.append(f"timepoint_index {cloud.timepoint_index}")
    
    # Add additional metadata
    for key, value in cloud.metadata.items():
        comments.append(f"{key} {value}")
    
    # Create and write PLY
    vertex_element = PlyElement.describe(vertex_data, 'vertex')
    plydata = PlyData(
        [vertex_element],
        text=not binary,
        comments=comments
    )
    
    plydata.write(str(filepath))


# Convenience functions

def create_minimal_ppf(
    xyz: np.ndarray,
    plant_id: str,
    ppf_version: str = "1.0"
) -> PPFPointCloud:
    """
    Create a minimal PPF point cloud with only required fields.
    
    Parameters
    ----------
    xyz : np.ndarray
        Point coordinates, shape (N, 3)
    plant_id : str
        Unique identifier
    ppf_version : str, default "1.0"
        PPF specification version
        
    Returns
    -------
    PPFPointCloud
        Minimal point cloud object
    """
    return PPFPointCloud(
        xyz=np.asarray(xyz, dtype=np.float32),
        ppf_version=ppf_version,
        plant_id=plant_id
    )


def add_labels_to_ppf(
    cloud: PPFPointCloud,
    semantic_labels: np.ndarray,
    instance_ids: Optional[np.ndarray] = None,
    organ_ids: Optional[np.ndarray] = None
) -> PPFPointCloud:
    """
    Add labels to an existing point cloud.
    
    Parameters
    ----------
    cloud : PPFPointCloud
        Existing point cloud
    semantic_labels : np.ndarray
        Semantic class IDs, shape (N,)
    instance_ids : np.ndarray, optional
        Instance IDs, shape (N,)
    organ_ids : np.ndarray, optional
        Hierarchical organ IDs, shape (N,)
        
    Returns
    -------
    PPFPointCloud
        New point cloud with labels added
    """
    return PPFPointCloud(
        xyz=cloud.xyz,
        ppf_version=cloud.ppf_version,
        plant_id=cloud.plant_id,
        subject_id=cloud.subject_id,
        timepoint_index=cloud.timepoint_index,
        semantic_labels=np.asarray(semantic_labels, dtype=np.int32),
        instance_ids=np.asarray(instance_ids, dtype=np.int32) if instance_ids is not None else None,
        organ_ids=np.asarray(organ_ids, dtype=np.int32) if organ_ids is not None else None,
        rgb=cloud.rgb,
        intensity=cloud.intensity,
        normals=cloud.normals,
        confidence=cloud.confidence,
        metadata=cloud.metadata.copy()
    )