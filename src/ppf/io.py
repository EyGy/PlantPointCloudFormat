"""
ppf.io — Read and write PPF (Plant Point Cloud Format) files.

Usage:
    from ppf import read_ppf, write_ppf, PPFPointCloud, LabelDefinition

    # Reading
    cloud = read_ppf("plant_001.ply")
    print(cloud.metadata)
    print(cloud.points.shape)

    # Writing
    cloud = PPFPointCloud(
        points=my_xyz_array,
        metadata={"plant_id": "maize_001"},
    )
    write_ppf(cloud, "output.ply")
"""

from __future__ import annotations

import struct
import warnings
from pathlib import Path
from typing import Union
import numpy as np

from .ppf import (
    PPF_VERSION,
    PLY_TYPE_MAP,
    PLY_STRUCT_MAP,
    VALID_ENCODINGS,
    RECOMMENDED_METADATA,
    LabelDefinition,
    PPFPointCloud,
)


# =============================================================================
# Reader
# =============================================================================


def read_ppf(filepath: Union[str, Path]) -> PPFPointCloud:
    """Read a PPF file.

    Args:
        filepath: Path to a .ply file.

    Returns:
        PPFPointCloud object.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file is not a valid PLY or is missing mandatory PPF fields.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, "rb") as f:
        header_lines, encoding, n_vertices, properties, bytes_before_vertex = _parse_header(f)
        metadata, labels = _parse_ppf_comments(header_lines)
        vertex_data = _read_vertices(f, encoding, n_vertices, properties, bytes_before_vertex)

    # Extract core arrays
    points = np.column_stack(
        [vertex_data["x"], vertex_data["y"], vertex_data["z"]]
    ).astype(np.float32)

    semantic_id = vertex_data.pop("semantic_id", None)
    instance_id = vertex_data.pop("instance_id", None)

    colors = None
    if "red" in vertex_data and "green" in vertex_data and "blue" in vertex_data:
        colors = np.column_stack(
            [vertex_data.pop("red"), vertex_data.pop("green"), vertex_data.pop("blue")]
        ).astype(np.uint8)

    # Everything else → extra_properties
    known = {"x", "y", "z"}
    extra = {k: v for k, v in vertex_data.items() if k not in known}

    return PPFPointCloud(
        points=points,
        metadata=metadata,
        labels=labels,
        semantic_id=semantic_id,
        instance_id=instance_id,
        colors=colors,
        extra_properties=extra,
    )


def _parse_header(f):
    """Parse PLY header. Returns (header_lines, encoding, n_vertices, properties, bytes_to_skip)."""
    magic = f.readline().decode("ascii").strip()
    if magic != "ply":
        raise ValueError(f"Not a PLY file (first line: '{magic}')")

    header_lines = []
    encoding = None
    n_vertices = 0
    properties = []  # [(name, ply_type), ...] for vertex only

    # Track ALL elements in order to compute skip bytes
    elements = []  # [(name, count, [(prop_name, prop_type), ...]), ...]
    current_element = None
    current_props = []

    while True:
        line = f.readline().decode("ascii").strip()
        header_lines.append(line)

        if line == "end_header":
            # Finalize last element
            if current_element is not None:
                elements.append((current_element[0], current_element[1], current_props))
            break

        if line.startswith("format "):
            encoding = line.split()[1]
            if encoding not in VALID_ENCODINGS:
                raise ValueError(f"Unsupported encoding: {encoding}")

        elif line.startswith("element "):
            # Finalize previous element
            if current_element is not None:
                elements.append((current_element[0], current_element[1], current_props))
            parts = line.split()
            current_element = (parts[1], int(parts[2]))
            current_props = []

        elif line.startswith("property "):
            parts = line.split()
            if parts[1] == "list":
                # List properties: type count_type value_type name
                # We can't easily compute fixed size — warn and bail
                if current_element and current_element[0] != "vertex":
                    warnings.warn(
                        f"Non-vertex element '{current_element[0]}' has list properties. "
                        f"PPF only supports vertex data; skipping may be inaccurate.",
                        UserWarning,
                    )
                current_props.append((parts[-1], "list"))
            else:
                current_props.append((parts[2], parts[1]))

    if encoding is None:
        raise ValueError("No 'format' line in PLY header.")

    # Find vertex element and compute bytes to skip before it
    bytes_before_vertex = 0
    vertex_found = False

    for elem_name, elem_count, elem_props in elements:
        if elem_name == "vertex":
            n_vertices = elem_count
            properties = elem_props
            vertex_found = True
            break
        else:
            # Need to skip this element's data
            if encoding != "ascii":
                has_list = any(t == "list" for _, t in elem_props)
                if has_list:
                    raise ValueError(
                        f"Non-vertex element '{elem_name}' with list properties "
                        f"appears before vertex element in binary PLY. "
                        f"Cannot determine skip size. Re-order elements or use ASCII."
                    )
                row_size = sum(
                    struct.calcsize(PLY_STRUCT_MAP[t]) for _, t in elem_props
                )
                bytes_before_vertex += row_size * elem_count
            else:
                bytes_before_vertex += elem_count  # number of lines to skip

    if not vertex_found or n_vertices == 0:
        raise ValueError("No vertex element found or vertex count is 0.")

    return header_lines, encoding, n_vertices, properties, bytes_before_vertex


def _parse_ppf_comments(header_lines):
    """Extract PPF metadata and labels from comment lines."""
    metadata = {}
    labels = []

    for line in header_lines:
        if not line.startswith("comment "):
            continue

        content = line[len("comment "):]

        if content.startswith("label "):
            try:
                label = LabelDefinition.from_comment(content[len("label "):])
                labels.append(label)
            except ValueError as e:
                warnings.warn(f"Skipping malformed label: {e}")
            continue

        parts = content.split(None, 1)
        if len(parts) == 2:
            metadata[parts[0]] = parts[1]
        elif len(parts) == 1:
            metadata[parts[0]] = ""

    return metadata, labels


def _read_vertices(f, encoding, n_vertices, properties, bytes_before_vertex=0):
    """Read vertex data, skipping any preceding non-vertex elements."""
    if encoding == "ascii":
        # Skip lines for preceding elements (faces etc.)
        for _ in range(bytes_before_vertex):
            f.readline()
        return _read_vertices_ascii(f, n_vertices, properties)
    else:
        # Skip bytes for preceding elements (faces etc.)
        if bytes_before_vertex > 0:
            f.read(bytes_before_vertex)
        endian = "<" if encoding == "binary_little_endian" else ">"
        return _read_vertices_binary(f, n_vertices, properties, endian)


def _read_vertices_ascii(f, n_vertices, properties):
    """Read ASCII vertex data."""
    n_props = len(properties)
    dtypes = [PLY_TYPE_MAP[t] for _, t in properties]
    data = {name: np.empty(n_vertices, dtype=dtypes[i]) 
            for i, (name, _) in enumerate(properties)}

    for row in range(n_vertices):
        while True:
            line = f.readline()
            if not line:
                raise ValueError(
                    f"Unexpected EOF at row {row}/{n_vertices}"
                )
            line = line.decode("ascii").strip()
            if line:  # Non-empty line found
                break

        values = line.split()
        if len(values) != n_props:
            raise ValueError(
                f"Row {row}: expected {n_props} values, got {len(values)}"
            )
        for i, (name, _) in enumerate(properties):
            data[name][row] = dtypes[i](values[i])

    return data


def _read_vertices_binary(f, n_vertices, properties, endian):
    """Read binary vertex data."""
    fmt = endian + "".join(PLY_STRUCT_MAP[t] for _, t in properties)
    row_size = struct.calcsize(fmt)

    raw = f.read(row_size * n_vertices)
    if len(raw) != row_size * n_vertices:
        raise ValueError(
            f"Unexpected EOF: expected {row_size * n_vertices} bytes, got {len(raw)}"
        )

    # Unpack all rows at once using numpy for performance
    dt = np.dtype([(name, PLY_TYPE_MAP[t]) for name, t in properties])
    structured = np.frombuffer(raw, dtype=dt.newbyteorder(endian), count=n_vertices)

    return {name: structured[name].copy() for name, _ in properties}


# =============================================================================
# Writer
# =============================================================================


def write_ppf(
    cloud: PPFPointCloud,
    filepath: Union[str, Path],
    encoding: str = "binary_little_endian",
) -> None:
    """Write a PPFPointCloud to a PLY file with PPF header comments.
    Note: may add 'ppf_version' to cloud.metadata if not present.
    Args:
        cloud: PPFPointCloud to write.
        filepath: Output path (should end in .ply).
        encoding: "ascii", "binary_little_endian", or "binary_big_endian".

    Raises:
        ValueError: If mandatory metadata is missing or encoding is invalid.
    """
    if encoding not in VALID_ENCODINGS:
        raise ValueError(f"Invalid encoding: '{encoding}'")

    filepath = Path(filepath)

    # Ensure mandatory fields
    if "ppf_version" not in cloud.metadata:
        cloud.metadata["ppf_version"] = PPF_VERSION
    if "plant_id" not in cloud.metadata:
        raise ValueError("Mandatory metadata 'plant_id' is missing.")

    header = _build_header(cloud, encoding)

    if encoding == "ascii":
        _write_ascii(cloud, filepath, header)
    else:
        endian = "<" if encoding == "binary_little_endian" else ">"
        _write_binary(cloud, filepath, header, endian)


def _build_header(cloud, encoding):
    """Build the PLY header string."""
    lines = ["ply", f"format {encoding} 1.0"]

    # Metadata comments — mandatory first, then rest
    key_order = ["ppf_version", "plant_id"]
    for key in RECOMMENDED_METADATA:
        if key in cloud.metadata and key not in key_order:
            key_order.append(key)
    for key in cloud.metadata:
        if key not in key_order:
            key_order.append(key)

    for key in key_order:
        if key in cloud.metadata:
            lines.append(f"comment {key} {cloud.metadata[key]}")

    # Label definitions
    for label in sorted(cloud.labels, key=lambda l: l.id):
        lines.append(label.to_comment())

    # Vertex element
    lines.append(f"element vertex {cloud.n_points}")
    lines.append("property float x")
    lines.append("property float y")
    lines.append("property float z")

    if cloud.has_colors:
        lines.append("property uchar red")
        lines.append("property uchar green")
        lines.append("property uchar blue")

    if cloud.has_annotations:
        lines.append("property int semantic_id")
    if cloud.has_instances:
        lines.append("property int instance_id")

    for name, arr in cloud.extra_properties.items():
        lines.append(f"property {_numpy_to_ply_type(arr.dtype)} {name}")

    lines.append("end_header")
    return "\n".join(lines) + "\n"


def _numpy_to_ply_type(dtype):
    """Map numpy dtype to PLY type string."""
    mapping = {
        np.dtype(np.float32): "float",
        np.dtype(np.float64): "double",
        np.dtype(np.int32): "int",
        np.dtype(np.int16): "short",
        np.dtype(np.int8): "char",
        np.dtype(np.uint32): "uint",
        np.dtype(np.uint16): "ushort",
        np.dtype(np.uint8): "uchar",
    }
    if dtype in mapping:
        return mapping[dtype]
    if np.issubdtype(dtype, np.floating):
        return "float"
    if np.issubdtype(dtype, np.integer):
        return "int"
    raise ValueError(f"Cannot map dtype '{dtype}' to PLY type.")


def _write_ascii(cloud, filepath, header):
    """Write ASCII PPF file."""
    with open(filepath, "w", newline="") as f:
        f.write(header)
        for i in range(cloud.n_points):
            row = [f"{cloud.points[i, 0]:.6f}",
                   f"{cloud.points[i, 1]:.6f}",
                   f"{cloud.points[i, 2]:.6f}"]

            if cloud.has_colors:
                row.extend([str(cloud.colors[i, 0]),
                            str(cloud.colors[i, 1]),
                            str(cloud.colors[i, 2])])

            if cloud.has_annotations:
                row.append(str(int(cloud.semantic_id[i])))
            if cloud.has_instances:
                row.append(str(int(cloud.instance_id[i])))

            for arr in cloud.extra_properties.values():
                row.append(str(arr[i]))

            f.write(" ".join(row) + "\n")


def _write_binary(cloud, filepath, header, endian):
    """Write binary PPF file."""
    # Build structured dtype for efficient writing
    dt_fields = [("x", np.float32), ("y", np.float32), ("z", np.float32)]

    if cloud.has_colors:
        dt_fields.extend([("red", np.uint8), ("green", np.uint8), ("blue", np.uint8)])
    if cloud.has_annotations:
        dt_fields.append(("semantic_id", np.int32))
    if cloud.has_instances:
        dt_fields.append(("instance_id", np.int32))
    for name, arr in cloud.extra_properties.items():
        dt_fields.append((name, arr.dtype))

    byte_order = "<" if endian == "<" else ">"
    dt = np.dtype(dt_fields).newbyteorder(byte_order)
    structured = np.empty(cloud.n_points, dtype=dt)

    structured["x"] = cloud.points[:, 0]
    structured["y"] = cloud.points[:, 1]
    structured["z"] = cloud.points[:, 2]

    if cloud.has_colors:
        structured["red"] = cloud.colors[:, 0]
        structured["green"] = cloud.colors[:, 1]
        structured["blue"] = cloud.colors[:, 2]
    if cloud.has_annotations:
        structured["semantic_id"] = cloud.semantic_id
    if cloud.has_instances:
        structured["instance_id"] = cloud.instance_id
    for name, arr in cloud.extra_properties.items():
        structured[name] = arr

    with open(filepath, "wb") as f:
        f.write(header.encode("ascii"))
        f.write(structured.tobytes())

# =============================================================================
# Transferring metadata
# =============================================================================

def transfer_metadata(
    edited_file: str,
    original_file: str,
    output_file: str,
    re_center: bool = True,
):
    """
    Re-applies PPF metadata from an original file to an edited file.

    Tools like CloudCompare may:
    - Discard all PPF comment headers
    - Rename properties (e.g., semantic_id → scalar_semantic_id)
    - Convert int properties to float/double
    - Apply coordinate shifts

    This function detects and corrects these issues.

    Parameters
    ----------
    edited_file : str
        Path to the file saved by the external editor.
    original_file : str
        Path to the original PPF file (metadata source).
    output_file : str
        Path to write the repaired PPF file.
    re_center : bool
        If True, re-center coordinates to median origin.
    """
    # Only read header from original (fast — skips all point data)
    original_metadata, original_labels, original_properties = _read_ppf_header_only(
        original_file
    )
    edited = read_ppf(edited_file)

    # -----------------------------------------------------------------
    # 1. Fix renamed properties (CloudCompare naming patterns)
    # -----------------------------------------------------------------
    _recover_renamed_properties(edited, original_properties)

    # -----------------------------------------------------------------
    # 2. Fix type conversions (float back to int for label fields)
    # -----------------------------------------------------------------
    if edited.semantic_id is not None and edited.semantic_id.dtype != np.int32:
        warnings.warn(
            f"semantic_id was {edited.semantic_id.dtype}, converting to int32.",
            UserWarning,
        )
        edited.semantic_id = np.rint(edited.semantic_id).astype(np.int32)

    if edited.instance_id is not None and edited.instance_id.dtype != np.int32:
        warnings.warn(
            f"instance_id was {edited.instance_id.dtype}, converting to int32.",
            UserWarning,
        )
        edited.instance_id = np.rint(edited.instance_id).astype(np.int32)

    # Restore original dtypes for all extra properties
    for prop_name, arr in list(edited.extra_properties.items()):
        if prop_name in original_properties:
            orig_type = original_properties[prop_name]
            target_dtype = PLY_TYPE_MAP.get(orig_type, None)
            if target_dtype and np.issubdtype(target_dtype, np.integer) and np.issubdtype(arr.dtype, np.floating):
                warnings.warn(
                    f"Property '{prop_name}': {arr.dtype} → {target_dtype}",
                    UserWarning,
                )
                edited.extra_properties[prop_name] = np.rint(arr).astype(target_dtype)

    # -----------------------------------------------------------------
    # 3. Carry over metadata and labels from original
    # -----------------------------------------------------------------
    edited.metadata = original_metadata.copy()
    edited.labels = list(original_labels)

    # -----------------------------------------------------------------
    # 4. Optionally re-center
    # -----------------------------------------------------------------
    if re_center:
        median = np.median(edited.points, axis=0)
        edited.points -= median.astype(edited.points.dtype)

    # -----------------------------------------------------------------
    # 5. Write repaired file
    # -----------------------------------------------------------------
    write_ppf(edited, output_file)
    print(f"Transferred PPF metadata from: {original_file} to {output_file}")


def _read_ppf_header_only(filepath: str):
    """
    Read ONLY the header of a PPF file. Skips all point data.
    
    Returns
    -------
    metadata : dict
    labels : list[LabelDefinition]
    properties : dict[str, str]
        Mapping of property name → PLY type string (e.g., {"organ_id": "int"})
    """
    metadata = {}
    labels = []
    properties = {}  # name → ply_type

    with open(filepath, "rb") as f:
        magic = f.readline().decode("ascii").strip()
        if magic != "ply":
            raise ValueError(f"Not a PLY file: {filepath}")

        while True:
            line = f.readline().decode("ascii").strip()
            if line == "end_header":
                break

            if line.startswith("comment "):
                content = line[8:]  # strip "comment "
                if content.startswith("label "):
                    parts = content.split()
                    # "label <id> <name> <type>"
                    if len(parts) >= 4:
                        labels.append(LabelDefinition(
                            id=int(parts[1]),
                            name=parts[2],
                            type=parts[3],
                        ))
                else:
                    # Key-value metadata: first word is key, rest is value
                    parts = content.split(None, 1)
                    if len(parts) == 2:
                        metadata[parts[0]] = parts[1]
                    elif len(parts) == 1:
                        metadata[parts[0]] = ""

            elif line.startswith("property ") and "list" not in line:
                parts = line.split()
                # "property <type> <name>"
                if len(parts) == 3:
                    properties[parts[2]] = parts[1]

    return metadata, labels, properties


def _recover_renamed_properties(cloud: PPFPointCloud, original_properties: dict):
    """
    Detect and recover properties renamed by CloudCompare.
    
    Uses the original file's property list as ground truth.
    Matches renamed properties by normalized name comparison.
    
    CloudCompare patterns:
    - "prop_name" → "scalar_prop_name"
    - "prop_name" → "Scalar field - prop_name"
    - "prop_name" → "prop_name_0"
    """
    # Known PPF core properties that are handled as dedicated fields
    CORE_PROPERTIES = {"x", "y", "z", "red", "green", "blue", "semantic_id", "instance_id"}

    # Build expected extra properties from original (exclude core)
    expected_extras = {
        name for name in original_properties if name not in CORE_PROPERTIES
    }

    if not expected_extras or not cloud.extra_properties:
        # Also try to recover semantic_id / instance_id from extras
        _recover_core_from_extras(cloud)
        return

    # Build normalized lookup for the edited file's extra properties
    # normalized_key → actual_key
    edited_lookup = {}
    for key in cloud.extra_properties:
        norm = _normalize_property_name(key)
        edited_lookup[norm] = key

    # For each expected property not already present, try to find it
    for expected_name in expected_extras:
        # Already correctly named?
        if expected_name in cloud.extra_properties:
            continue

        # Try normalized matching
        expected_norm = _normalize_property_name(expected_name)
        if expected_norm in edited_lookup:
            actual_key = edited_lookup[expected_norm]
            warnings.warn(
                f"Recovered property '{expected_name}' from '{actual_key}'.",
                UserWarning,
            )
            cloud.extra_properties[expected_name] = cloud.extra_properties.pop(actual_key)
            continue

        # Try CloudCompare-specific prefixes
        cc_variants = [
            f"scalar_{expected_name}",
            f"scalar field - {expected_name}",
            f"{expected_name}_0",
        ]
        for variant in cc_variants:
            variant_norm = _normalize_property_name(variant)
            if variant_norm in edited_lookup:
                actual_key = edited_lookup[variant_norm]
                warnings.warn(
                    f"Recovered property '{expected_name}' from '{actual_key}'.",
                    UserWarning,
                )
                cloud.extra_properties[expected_name] = cloud.extra_properties.pop(actual_key)
                break

    # Also recover core properties if they ended up in extras
    _recover_core_from_extras(cloud)


def _recover_core_from_extras(cloud: PPFPointCloud):
    """Recover semantic_id and instance_id from extra_properties if missing."""
    
    SEMANTIC_PATTERNS = (
        "semantic_id", "scalar_semantic_id", "scalar field - semantic_id",
        "semantic_id_0", "semanticid", "semantic", "label",
        "class", "classification",
    )
    INSTANCE_PATTERNS = (
        "instance_id", "scalar_instance_id", "scalar field - instance_id",
        "instance_id_0", "instanceid", "instance",
    )

    if cloud.semantic_id is None and cloud.extra_properties:
        for pattern in SEMANTIC_PATTERNS:
            match = _find_property_ci(cloud.extra_properties, pattern)
            if match is not None:
                warnings.warn(
                    f"Recovered semantic_id from '{match}'.",
                    UserWarning,
                )
                cloud.semantic_id = np.rint(cloud.extra_properties.pop(match)).astype(np.int32)
                break

    if cloud.instance_id is None and cloud.extra_properties:
        for pattern in INSTANCE_PATTERNS:
            match = _find_property_ci(cloud.extra_properties, pattern)
            if match is not None:
                warnings.warn(
                    f"Recovered instance_id from '{match}'.",
                    UserWarning,
                )
                cloud.instance_id = np.rint(cloud.extra_properties.pop(match)).astype(np.int32)
                break


def _normalize_property_name(name: str) -> str:
    """Normalize property name for comparison: lowercase, strip all delimiters."""
    return name.lower().replace(" ", "").replace("-", "").replace("_", "")


def _find_property_ci(properties: dict, pattern: str) -> Optional[str]:
    """Case-insensitive normalized property name search."""
    pattern_norm = _normalize_property_name(pattern)
    for key in properties:
        if _normalize_property_name(key) == pattern_norm:
            return key
    return None