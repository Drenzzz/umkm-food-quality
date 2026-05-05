from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
IGNORED_FILENAMES = {"desktop.ini", ".ds_store"}
KNOWN_DATASETS = {
    "IndustryBiscuit": "industry_biscuit",
    "Pepsico RnD Potato Lab Dataset": "pepsico_potato_lab",
    "taterdat-chip": "taterdat_chip",
}


@dataclass(frozen=True)
class DatasetItem:
    dataset_name: str
    dataset_slug: str
    source_label: str
    final_label: str
    source_path: Path
    relative_source: str
    source_group: str


class MappingTable:
    def __init__(self, mapping_csv_path: Path) -> None:
        self._mapping: dict[tuple[str, str], str] = {}
        with mapping_csv_path.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                key = (row["dataset_name"], row["source_label"])
                self._mapping[key] = row["final_label"]

    def get_final_label(self, dataset_name: str, source_label: str) -> str:
        key = (dataset_name, source_label)
        if key not in self._mapping:
            raise KeyError(f"Missing mapping for {dataset_name} -> {source_label}")
        return self._mapping[key]


def should_skip_path(path: Path) -> bool:
    return path.name.lower() in IGNORED_FILENAMES


def is_supported_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS


def validate_image(path: Path) -> None:
    with Image.open(path) as image:
        image.verify()


def transform_image(source_path: Path, destination_path: Path, image_size: int) -> None:
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(source_path) as image:
        if image.mode != "RGB":
            image = image.convert("RGB")
        image = image.resize((image_size, image_size), resample=Image.Resampling.LANCZOS)
        image.save(destination_path, "JPEG", optimize=True, quality=90)


def build_output_filename(item: DatasetItem) -> str:
    stable_source = f"{item.dataset_slug}:{item.source_group}:{item.relative_source}"
    digest = hashlib.sha1(stable_source.encode("utf-8")).hexdigest()[:12]
    return f"{item.dataset_slug}_{digest}.jpg"


def iter_public_dataset_items(source_root: Path, mapping_csv_path: Path) -> list[DatasetItem]:
    mapping = MappingTable(mapping_csv_path)
    items: list[DatasetItem] = []
    items.extend(_load_industry_biscuit_items(source_root, mapping))
    items.extend(_load_taterdat_items(source_root, mapping))
    items.extend(_load_pepsico_items(source_root, mapping))
    return items


def _load_industry_biscuit_items(source_root: Path, mapping: MappingTable) -> list[DatasetItem]:
    dataset_name = "IndustryBiscuit"
    dataset_slug = KNOWN_DATASETS[dataset_name]
    dataset_dir = source_root / dataset_name
    annotations_path = dataset_dir / "Annotations.csv"
    images_dir = dataset_dir / "Images"
    items: list[DatasetItem] = []

    with annotations_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            source_path = images_dir / row["file"]
            if not source_path.exists():
                continue
            final_label = mapping.get_final_label(dataset_name, row["classDescription"])
            items.append(
                DatasetItem(
                    dataset_name=dataset_name,
                    dataset_slug=dataset_slug,
                    source_label=row["classDescription"],
                    final_label=final_label,
                    source_path=source_path,
                    relative_source=row["file"],
                    source_group="annotations",
                )
            )

    return items


def _load_taterdat_items(source_root: Path, mapping: MappingTable) -> list[DatasetItem]:
    dataset_name = "taterdat-chip"
    dataset_slug = KNOWN_DATASETS[dataset_name]
    dataset_dir = source_root / dataset_name
    items: list[DatasetItem] = []

    for source_label in ("Non-Defective", "Defective"):
        label_dir = dataset_dir / source_label
        final_label = mapping.get_final_label(dataset_name, source_label)
        for source_path in sorted(label_dir.iterdir()):
            if not source_path.is_file() or should_skip_path(source_path) or not is_supported_image(source_path):
                continue
            items.append(
                DatasetItem(
                    dataset_name=dataset_name,
                    dataset_slug=dataset_slug,
                    source_label=source_label,
                    final_label=final_label,
                    source_path=source_path,
                    relative_source=f"{source_label}/{source_path.name}",
                    source_group="folder",
                )
            )

    return items


def _load_pepsico_items(source_root: Path, mapping: MappingTable) -> list[DatasetItem]:
    dataset_name = "Pepsico RnD Potato Lab Dataset"
    dataset_slug = KNOWN_DATASETS[dataset_name]
    dataset_dir = source_root / dataset_name
    items: list[DatasetItem] = []

    split_groups = {
        "Train": "train_folder",
        "Test": "test_folder",
    }

    for split_name, source_group in split_groups.items():
        split_dir = dataset_dir / split_name
        for label_dir in sorted(split_dir.iterdir()):
            if not label_dir.is_dir():
                continue
            source_label = label_dir.name
            final_label = mapping.get_final_label(dataset_name, source_label)
            for source_path in sorted(label_dir.iterdir()):
                if not source_path.is_file() or should_skip_path(source_path) or not is_supported_image(source_path):
                    continue
                items.append(
                    DatasetItem(
                        dataset_name=dataset_name,
                        dataset_slug=dataset_slug,
                        source_label=source_label,
                        final_label=final_label,
                        source_path=source_path,
                        relative_source=f"{split_name}/{source_label}/{source_path.name}",
                        source_group=source_group,
                    )
                )

    return items


def classify_item_error(item: DatasetItem, error: Exception) -> str:
    if isinstance(error, (UnidentifiedImageError, OSError, ValueError)):
        return "invalid"
    return "rejected"
