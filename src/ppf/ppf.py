from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import warnings

# =============================================================================
# Constants
# =============================================================================

PPF_VERSION = "1.0"

MANDATORY_METADATA = {"ppf_version", "plant_id"}

RECOMMENDED_METADATA = (
    "species",
    "acquisition_date",
    "acquisition_time",
    "sensor_type",
    "plant_category",
    "dataset_name",
)

VALID_LABEL_TYPES = {"void", "thing", "stuff"}

VALID_ENCODINGS = {"ascii", "binary_little_endian", "binary_big_endian"}

# PLY type → numpy dtype
PLY_TYPE_MAP = {
    "float": np.float32,
    "float32": np.float32,
    "double": np.float64,
    "float64": np.float64,
    "int": np.int32,
    "int32": np.int32,
    "int16": np.int16,
    "int8": np.int8,
    "uint": np.uint32,
    "uint32": np.uint32,
    "uint16": np.uint16,
    "uint8": np.uint8,
    "uchar": np.uint8,
    "char": np.int8,
    "short": np.int16,
    "ushort": np.uint16,
}

# PLY type → struct format character
PLY_STRUCT_MAP = {
    "float": "f",
    "float32": "f",
    "double": "d",
    "float64": "d",
    "int": "i",
    "int32": "i",
    "int16": "h",
    "int8": "b",
    "uint": "I",
    "uint32": "I",
    "uint16": "H",
    "uint8": "B",
    "uchar": "B",
    "char": "b",
    "short": "h",
    "ushort": "H",
}

# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class LabelDefinition:
    """A single label in the PPF schema.

    Attributes:
        id: Integer semantic ID (>= 0).
        name: Short snake_case name (e.g., "leaf", "stem").
        type: One of "void", "thing", or "stuff".
    """

    id: int
    name: str
    type: str

    def __post_init__(self):
        if self.type not in VALID_LABEL_TYPES:
            raise ValueError(
                f"Invalid label type '{self.type}'. Must be one of {VALID_LABEL_TYPES}"
            )
        if self.id < 0:
            raise ValueError(f"Label ID must be >= 0, got {self.id}")

    def to_comment(self) -> str:
        """Convert to PLY header comment line."""
        return f"comment label {self.id} {self.name} {self.type}"

    @classmethod
    def from_comment(cls, comment_value: str) -> LabelDefinition:
        """Parse from the value part after 'comment label '.

        Args:
            comment_value: String like "1 leaf thing"
        """
        parts = comment_value.strip().split()
        if len(parts) != 3:
            raise ValueError(
                f"Invalid label format: '{comment_value}'. "
                f"Expected: '<id> <name> <type>'"
            )
        return cls(id=int(parts[0]), name=parts[1], type=parts[2])

# =============================================================================
# Default Base Label Schema (Section 4.1 of PPF Specification)
# =============================================================================

DEFAULT_LABELS: tuple[LabelDefinition, ...] = (
    LabelDefinition(id=0, name="unlabeled", type="void"),
    LabelDefinition(id=1, name="leaf", type="thing"),
    LabelDefinition(id=2, name="stem", type="thing"),
    LabelDefinition(id=3, name="petiole", type="thing"),
    LabelDefinition(id=4, name="branch", type="thing"),
    LabelDefinition(id=5, name="flower", type="thing"),
    LabelDefinition(id=6, name="fruit", type="thing"),
    LabelDefinition(id=7, name="root", type="stuff"),
    LabelDefinition(id=8, name="substrate", type="stuff"),
    LabelDefinition(id=9, name="pot", type="stuff"),
)

# Convenient lookup dicts
DEFAULT_LABEL_BY_ID: dict[int, LabelDefinition] = {l.id: l for l in DEFAULT_LABELS}
DEFAULT_LABEL_BY_NAME: dict[str, LabelDefinition] = {l.name: l for l in DEFAULT_LABELS}


@dataclass
class PPFPointCloud:
    """A PPF point cloud representing a single plant.

    Attributes:
        points: Array of shape (N, 3) — XYZ coordinates in millimeters.
        metadata: Dict of header comment key-value pairs.
        labels: List of LabelDefinition objects (empty if unannotated).
        semantic_id: Array of shape (N,) with semantic class IDs, or None.
        instance_id: Array of shape (N,) with instance IDs, or None.
        colors: Array of shape (N, 3) with RGB values (0–255), or None.
        extra_properties: Dict of additional vertex properties {name: array}.
    """

    points: np.ndarray
    metadata: dict = field(default_factory=dict)
    labels: list = field(default_factory=list)
    semantic_id: Optional[np.ndarray] = None
    instance_id: Optional[np.ndarray] = None
    colors: Optional[np.ndarray] = None
    extra_properties: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.points.ndim != 2 or self.points.shape[1] != 3:
            raise ValueError(f"Points must have shape (N, 3), got {self.points.shape}")

        n = self.n_points
        # Validate array lengths (likely a bug or corrupt data)
        if self.semantic_id is not None and len(self.semantic_id) != n:
            raise ValueError(
                f"semantic_id length {len(self.semantic_id)} != {n} points"
            )
        if self.instance_id is not None and len(self.instance_id) != n:
            raise ValueError(
                f"instance_id length {len(self.instance_id)} != {n} points"
            )
        if self.colors is not None and self.colors.shape[0] != n:
            raise ValueError(
                f"colors has {self.colors.shape[0]} rows, expected {n}"
            )

        # Soft fix: instance_id without semantic_id → fill semantic_id with 0
        if self.instance_id is not None and self.semantic_id is None:
            warnings.warn(
                "instance_id provided without semantic_id. "
                "Setting semantic_id to 0 (unlabeled).",
                UserWarning,
                stacklevel=2,
            )
            self.semantic_id = np.zeros(n, dtype=np.int32)
        
    @property
    def n_points(self) -> int:
        return self.points.shape[0]

    @property
    def plant_id(self) -> str:
        return self.metadata.get("plant_id", "")

    @property
    def has_annotations(self) -> bool:
        return self.semantic_id is not None

    @property
    def has_instances(self) -> bool:
        return self.instance_id is not None

    @property
    def has_colors(self) -> bool:
        return self.colors is not None
    
    @property
    def effective_labels(self) -> tuple[LabelDefinition, ...]:
        """Labels in use: file-defined labels if present, otherwise the PPF base schema."""
        if self.labels:
            return tuple(self.labels)
        return DEFAULT_LABELS

    def get_label_by_id(self, label_id: int) -> Optional[LabelDefinition]:
        """Get label definition by ID. Falls back to base schema if no custom labels."""
        for label in self.effective_labels:
            if label.id == label_id:
                return label
        else:
            print("Requested label with id", label_id ," not found")
        return None

    def get_label_by_name(self, name: str) -> Optional[LabelDefinition]:
        """Get label definition by name. Falls back to base schema if no custom labels."""
        for label in self.effective_labels:
            if label.name == name:
                return label
        else:
            print("Requested label with name", name ," not found")
        return None

    def get_instance_mask(self, semantic_name: str) -> dict:
        """Get boolean masks for each instance of a semantic class.

        Args:
            semantic_name: Name of the semantic class (e.g., "leaf").

        Returns:
            Dict of {instance_id: boolean_mask_array}.
        """
        label = self.get_label_by_name(semantic_name)
        if label is None:
            raise ValueError(f"Label '{semantic_name}' not found.")
        if not self.has_annotations or not self.has_instances:
            raise ValueError("Point cloud has no annotations/instances.")

        semantic_mask = self.semantic_id == label.id
        unique_ids = np.unique(self.instance_id[semantic_mask])
        unique_ids = unique_ids[unique_ids > 0]

        return {
            int(iid): (self.semantic_id == label.id) & (self.instance_id == iid)
            for iid in unique_ids
        }

    def __repr__(self) -> str:
        parts = [
            f"PPFPointCloud(",
            f"  plant_id='{self.plant_id}',",
            f"  n_points={self.n_points:,},",
            f"  has_colors={self.has_colors},",
            f"  has_annotations={self.has_annotations},",
            f"  has_instances={self.has_instances},",
            f"  n_labels={len(self.labels)},",
            f"  metadata_keys={list(self.metadata.keys())},",
        ]
        if self.extra_properties:
            parts.append(f"  extra_properties={list(self.extra_properties.keys())},")
        parts.append(")")
        return "\n".join(parts)
    
    def _repr_html_(self) -> str:
        """Rich HTML display for Jupyter notebooks."""
        mins = self.points.min(axis=0)
        maxs = self.points.max(axis=0)
        extent = maxs - mins

        html = f"""
        <div style="font-family: monospace; padding: 10px; border: 1px solid #ccc; border-radius: 5px; background: #f9f9f9; max-width: 700px;">
            <h3 style="margin-top:0; color: #2e7d32;">🌱 PPF Point Cloud: {self.plant_id}</h3>
            <table style="border-collapse: collapse; width: 100%;">
                <tr><td><b>Points</b></td><td>{self.n_points:,}</td></tr>
                <tr><td><b>Colors</b></td><td>{'✓' if self.has_colors else '✗'}</td></tr>
                <tr><td><b>Annotations</b></td><td>{'✓' if self.has_annotations else '✗'}</td></tr>
                <tr><td><b>Instances</b></td><td>{'✓' if self.has_instances else '✗'}</td></tr>
                <tr><td><b>Extent (mm)</b></td><td>X={extent[0]:.1f} &times; Y={extent[1]:.1f} &times; Z={extent[2]:.1f}</td></tr>
            </table>
        """

        if self.effective_labels and self.has_annotations:
            total_annotated = int(np.sum(self.semantic_id != 0))
            html += """
            <h4 style="margin-bottom: 4px;">Labels</h4>
            <table style="border-collapse: collapse; width: 100%; font-size: 0.9em;">
                <tr style="border-bottom: 2px solid #666;">
                    <th style="text-align:right; padding: 2px 8px;">ID</th>
                    <th style="text-align:left; padding: 2px 8px;">Name</th>
                    <th style="text-align:left; padding: 2px 8px;">Type</th>
                    <th style="text-align:right; padding: 2px 8px;">Points</th>
                    <th style="text-align:right; padding: 2px 8px;">%</th>
                    <th style="text-align:right; padding: 2px 8px;">Instances</th>
                </tr>
            """
            for label in sorted(self.effective_labels, key=lambda l: l.id):
                n_pts = int(np.sum(self.semantic_id == label.id))
                if n_pts == 0:
                    continue
                pct = 100.0 * n_pts / self.n_points
                inst_str = ""
                if self.has_instances and label.type == "thing":
                    instances = np.unique(self.instance_id[self.semantic_id == label.id])
                    inst_str = str(len(instances[instances > 0]))
                color = "#e8f5e9" if label.type == "thing" else "#fff3e0" if label.type == "stuff" else "#eeeeee"
                html += f"""
                <tr style="background: {color};">
                    <td style="text-align:right; padding: 2px 8px;">{label.id}</td>
                    <td style="padding: 2px 8px;">{label.name}</td>
                    <td style="padding: 2px 8px;">{label.type}</td>
                    <td style="text-align:right; padding: 2px 8px;">{n_pts:,}</td>
                    <td style="text-align:right; padding: 2px 8px;">{pct:.1f}%</td>
                    <td style="text-align:right; padding: 2px 8px;">{inst_str}</td>
                </tr>
                """
            html += f"""
            </table>
            <p style="font-size: 0.85em; color: #555;">Coverage: {100.0 * total_annotated / self.n_points:.1f}% annotated</p>
            """

        html += "</div>"
        return html

