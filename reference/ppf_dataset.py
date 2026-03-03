"""
PPF Dataset Module

Load and manage PPF-compliant datasets.

Requirements:
    pip install numpy plyfile
"""

import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set
from .ppf_io import read_ppf, PPFPointCloud


@dataclass
class PPFDataset:
    """
    Container for a PPF dataset.
    
    Attributes
    ----------
    name : str
        Dataset name
    root_path : Path
        Path to dataset root directory
    index : dict
        Contents of dataset.json
    schema : dict
        Contents of schema.json
        
    Examples
    --------
    >>> dataset = PPFDataset.load("path/to/dataset")
    >>> print(f"Dataset: {dataset.name}")
    >>> print(f"Plants: {len(dataset.plants)}")
    >>> 
    >>> # Get training split
    >>> train_subjects = dataset.get_split("train")
    >>> train_plants = dataset.get_plants_for_subjects(train_subjects)
    >>> 
    >>> # Load a plant
    >>> cloud = dataset.load_plant(train_plants[0])
    """
    
    name: str
    root_path: Path
    index: Dict[str, Any]
    schema: Dict[str, Any]
    
    @classmethod
    def load(cls, dataset_path: str) -> 'PPFDataset':
        """
        Load a PPF dataset from disk.
        
        Parameters
        ----------
        dataset_path : str
            Path to dataset root directory
            
        Returns
        -------
        PPFDataset
            Loaded dataset object
            
        Raises
        ------
        FileNotFoundError
            If dataset.json or schema.json not found
        """
        root = Path(dataset_path)
        
        index_path = root / 'dataset.json'
        schema_path = root / 'schema.json'
        
        if not index_path.exists():
            raise FileNotFoundError(f"dataset.json not found in {root}")
        if not schema_path.exists():
            raise FileNotFoundError(f"schema.json not found in {root}")
        
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        return cls(
            name=index['dataset_name'],
            root_path=root,
            index=index,
            schema=schema
        )
    
    @property
    def plants(self) -> List[Dict[str, Any]]:
        """List of all plant entries."""
        return self.index.get('plants', [])
    
    @property
    def n_plants(self) -> int:
        """Total number of plant scans."""
        return len(self.plants)
    
    @property
    def subject_ids(self) -> List[str]:
        """List of unique subject IDs."""
        subjects = set()
        for p in self.plants:
            if 'subject_id' in p:
                subjects.add(p['subject_id'])
        return sorted(subjects)
    
    @property
    def n_subjects(self) -> int:
        """Number of unique physical plants."""
        return len(self.subject_ids)
    
    @property
    def is_temporal(self) -> bool:
        """Whether this is a temporal dataset."""
        temporal_info = self.index.get('temporal_info', {})
        return temporal_info.get('is_temporal', False)
    
    @property
    def species_list(self) -> List[str]:
        """List of species in the dataset."""
        species = set()
        for p in self.plants:
            if 'species' in p:
                species.add(p['species'])
        return sorted(species)
    
    @property
    def label_names(self) -> Dict[int, str]:
        """Mapping from label ID to name."""
        return {
            int(k): v['name'] 
            for k, v in self.schema.get('labels', {}).items()
        }
    
    @property
    def label_colors(self) -> Dict[int, List[int]]:
        """Mapping from label ID to RGB color."""
        return {
            int(k): v['color'] 
            for k, v in self.schema.get('labels', {}).items()
        }
    
    def get_split(self, split_name: str) -> List[str]:
        """
        Load subject IDs for a data split.
        
        Parameters
        ----------
        split_name : str
            Split name (e.g., "train", "val", "test")
            
        Returns
        -------
        List[str]
            List of subject IDs in the split
        """
        split_file = self.root_path / 'splits' / f'{split_name}.txt'
        
        if not split_file.exists():
            raise FileNotFoundError(f"Split file not found: {split_file}")
        
        with open(split_file, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    
    def get_available_splits(self) -> List[str]:
        """Get list of available split names."""
        splits_dir = self.root_path / 'splits'
        if not splits_dir.exists():
            return []
        return [f.stem for f in splits_dir.glob('*.txt')]
    
    def get_plants_for_subjects(
        self, 
        subject_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Get plant entries for given subject IDs.
        
        Parameters
        ----------
        subject_ids : List[str]
            List of subject IDs
            
        Returns
        -------
        List[Dict[str, Any]]
            Plant entries matching the subjects
        """
        subject_set = set(subject_ids)
        return [
            p for p in self.plants 
            if p.get('subject_id') in subject_set
        ]
    
    def get_plants_for_species(self, species: str) -> List[Dict[str, Any]]:
        """Get plant entries for a specific species."""
        return [p for p in self.plants if p.get('species') == species]
    
    def get_plants_for_timepoint(self, timepoint_index: int) -> List[Dict[str, Any]]:
        """Get plant entries for a specific timepoint."""
        return [p for p in self.plants if p.get('timepoint_index') == timepoint_index]
    
    def get_timepoints_for_subject(self, subject_id: str) -> List[Dict[str, Any]]:
        """Get all timepoints for a specific subject, sorted by index."""
        plants = [p for p in self.plants if p.get('subject_id') == subject_id]
        return sorted(plants, key=lambda p: p.get('timepoint_index', 0))
    
    def load_plant(self, plant_entry: Dict[str, Any]) -> PPFPointCloud:
        """
        Load a plant point cloud.
        
        Parameters
        ----------
        plant_entry : Dict[str, Any]
            Plant entry from self.plants
            
        Returns
        -------
        PPFPointCloud
            Loaded point cloud
        """
        filepath = self.root_path / plant_entry['file']
        return read_ppf(str(filepath))
    
    def load_plant_by_id(self, plant_id: str) -> PPFPointCloud:
        """
        Load a plant by its plant_id.
        
        Parameters
        ----------
        plant_id : str
            Unique plant identifier
            
        Returns
        -------
        PPFPointCloud
            Loaded point cloud
        """
        for plant in self.plants:
            if plant['plant_id'] == plant_id:
                return self.load_plant(plant)
        raise ValueError(f"Plant not found: {plant_id}")
    
    def get_label_name(self, label_id: int) -> str:
        """Get human-readable name for a label ID."""
        return self.schema.get('labels', {}).get(str(label_id), {}).get('name', 'unknown')
    
    def get_label_color(self, label_id: int) -> List[int]:
        """Get RGB color for a label ID."""
        return self.schema.get('labels', {}).get(str(label_id), {}).get('color', [128, 128, 128])
    
    def get_label_type(self, label_id: int) -> str:
        """Get label type (void/stuff/thing) for a label ID."""
        return self.schema.get('labels', {}).get(str(label_id), {}).get('type', 'void')
    
    def get_thing_classes(self) -> List[int]:
        """Get label IDs for 'thing' classes (have instances)."""
        return [
            int(k) for k, v in self.schema.get('labels', {}).items()
            if v.get('type') == 'thing'
        ]
    
    def get_stuff_classes(self) -> List[int]:
        """Get label IDs for 'stuff' classes (no instances)."""
        return [
            int(k) for k, v in self.schema.get('labels', {}).items()
            if v.get('type') == 'stuff'
        ]
    
    def summary(self) -> str:
        """Generate a summary string of the dataset."""
        lines = [
            f"PPF Dataset: {self.name}",
            f"  PPF Version: {self.index.get('ppf_version', 'unknown')}",
            f"  Total scans: {self.n_plants}",
            f"  Unique subjects: {self.n_subjects}",
            f"  Temporal: {self.is_temporal}",
            f"  Species: {', '.join(self.species_list) or 'not specified'}",
            f"  Available splits: {', '.join(self.get_available_splits()) or 'none'}",
            f"  Labels: {len(self.schema.get('labels', {}))} classes",
        ]
        return '\n'.join(lines)


def create_train_test_split(
    dataset: PPFDataset,
    test_ratio: float = 0.2,
    val_ratio: float = 0.1,
    seed: int = 42,
    stratify_by: Optional[str] = None
) -> Dict[str, List[str]]:
    """
    Create train/val/test splits for a dataset.
    
    Splits are always by subject_id to prevent data leakage.
    
    Parameters
    ----------
    dataset : PPFDataset
        Dataset to split
    test_ratio : float
        Fraction for test set
    val_ratio : float
        Fraction for validation set
    seed : int
        Random seed for reproducibility
    stratify_by : str, optional
        Field to stratify by (e.g., 'species')
        
    Returns
    -------
    Dict[str, List[str]]
        Dictionary with 'train', 'val', 'test' keys mapping to subject IDs
    """
    import random
    random.seed(seed)
    
    subjects = dataset.subject_ids.copy()
    
    if stratify_by:
        # Group subjects by stratification field
        groups = {}
        for plant in dataset.plants:
            subj = plant.get('subject_id')
            value = plant.get(stratify_by, 'unknown')
            if subj not in groups:
                groups[subj] = value
        
        # Split within each stratum
        strata = {}
        for subj, value in groups.items():
            if value not in strata:
                strata[value] = []
            strata[value].append(subj)
        
        train, val, test = [], [], []
        for stratum_subjects in strata.values():
            random.shuffle(stratum_subjects)
            n = len(stratum_subjects)
            n_test = max(1, int(n * test_ratio))
            n_val = max(1, int(n * val_ratio))
            
            test.extend(stratum_subjects[:n_test])
            val.extend(stratum_subjects[n_test:n_test + n_val])
            train.extend(stratum_subjects[n_test + n_val:])
    else:
        # Simple random split
        random.shuffle(subjects)
        n = len(subjects)
        n_test = int(n * test_ratio)
        n_val = int(n * val_ratio)
        
        test = subjects[:n_test]
        val = subjects[n_test:n_test + n_val]
        train = subjects[n_test + n_val:]
    
    return {
        'train': sorted(train),
        'val': sorted(val),
        'test': sorted(test)
    }


def save_splits(
    dataset_path: str,
    splits: Dict[str, List[str]]
) -> None:
    """
    Save splits to text files.
    
    Parameters
    ----------
    dataset_path : str
        Path to dataset root
    splits : Dict[str, List[str]]
        Dictionary mapping split names to subject IDs
    """
    splits_dir = Path(dataset_path) / 'splits'
    splits_dir.mkdir(exist_ok=True)
    
    for split_name, subjects in splits.items():
        split_file = splits_dir / f'{split_name}.txt'
        with open(split_file, 'w') as f:
            for subject in subjects:
                f.write(f'{subject}\n')