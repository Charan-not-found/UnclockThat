"""Dataset upload, strict ZIP validation, 480p standardization, and management endpoints."""

from __future__ import annotations

import hashlib
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.database.connection import get_db
from backend.app.database.models.scanner import DatasetRecord

router = APIRouter(prefix="/datasets", tags=["datasets"])

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
TARGET_WIDTH = 640
TARGET_HEIGHT = 480


class DatasetOut(BaseModel):
    id: int
    name: str
    category: str
    industry: str
    source_filename: str
    file_count: int
    valid_image_count: int
    invalid_file_count: int
    duplicate_count: int
    validation_status: str
    validation_details: Optional[dict[str, Any]]
    sha256_hash: Optional[str]
    created_at: str


def _to_out(ds: DatasetRecord) -> DatasetOut:
    return DatasetOut(
        id=ds.id,
        name=ds.name,
        category=ds.category,
        industry=ds.industry,
        source_filename=ds.source_filename,
        file_count=ds.file_count,
        valid_image_count=ds.valid_image_count,
        invalid_file_count=ds.invalid_file_count,
        duplicate_count=ds.duplicate_count,
        validation_status=ds.validation_status,
        validation_details=ds.validation_details_json,
        sha256_hash=ds.sha256_hash,
        created_at=ds.created_at.isoformat(),
    )


def _resize_and_compress_480p(raw_bytes: bytes, dest_path: Path) -> bytes:
    """Decode image bytes, resize/upscale/compress to 480p (640x480), and write as compressed JPEG."""
    arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Corrupt or unreadable image")

    h, w = img.shape[:2]
    interp = cv2.INTER_CUBIC if (w < TARGET_WIDTH or h < TARGET_HEIGHT) else cv2.INTER_AREA
    resized = cv2.resize(img, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=interp)

    ok, encoded = cv2.imencode(".jpg", resized, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        raise ValueError("Failed to encode standardized 480p image")

    out_bytes = encoded.tobytes()
    out_file = dest_path.with_suffix(".jpg")
    out_file.write_bytes(out_bytes)
    return out_bytes


def _validate_and_extract_zip(archive_file: Path, extracted_dir: Path) -> dict[str, Any]:
    """
    Strictly validate a ZIP archive:
      - No subfolders or directory entries allowed (flat root only: data.zip -> [1.png, 2.png])
      - Only supported image files allowed (no other files)
      - Must contain at least 1 valid image
      - Every image is resized/compressed to 480p (640x480)
    """
    try:
        zf = zipfile.ZipFile(archive_file, "r")
    except zipfile.BadZipFile:
        raise HTTPException(status_code=422, detail=f"Invalid ZIP archive: '{archive_file.name}'.")

    with zf:
        members = zf.infolist()
        if not members:
            raise HTTPException(
                status_code=422,
                detail="ZIP validation failed: archive is empty. Expected flat images like data.zip -> [1.png, 2.png].",
            )

        # Pass 1: strict structural check before extracting anything
        for member in members:
            norm_name = member.filename.replace("\\", "/")
            if member.is_dir() or "/" in norm_name:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"ZIP validation failed: subfolders are not allowed (found '{member.filename}'). "
                        "Place images directly at the root of the ZIP: data.zip -> [1.png, 2.png, ...]."
                    ),
                )
            ext = Path(norm_name).suffix.lower()
            if ext not in ALLOWED_IMAGE_EXTS:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"ZIP validation failed: non-image file '{norm_name}' is not allowed. "
                        f"Allowed extensions: {', '.join(sorted(ALLOWED_IMAGE_EXTS))}."
                    ),
                )

        # Pass 2: decode, detect duplicates, resize/compress to 480p
        seen_hashes: set[str] = set()
        valid = 0
        duplicates = 0
        for member in members:
            fname = Path(member.filename).name
            raw_bytes = zf.read(member)
            raw_digest = hashlib.sha256(raw_bytes).hexdigest()
            if raw_digest in seen_hashes:
                duplicates += 1
            else:
                seen_hashes.add(raw_digest)

            try:
                _resize_and_compress_480p(raw_bytes, extracted_dir / fname)
                valid += 1
            except ValueError as exc:
                raise HTTPException(
                    status_code=422,
                    detail=f"ZIP validation failed: '{fname}' is corrupt or unreadable ({exc}).",
                )

    return {
        "file_count": valid,
        "valid_image_count": valid,
        "invalid_file_count": 0,
        "duplicate_count": duplicates,
        "validation_status": "Validated",
        "errors": [],
        "resolution": f"{TARGET_WIDTH}x{TARGET_HEIGHT} (480p)",
    }


def _validate_extracted_dir(extracted_dir: Path) -> dict[str, Any]:
    total = 0
    valid = 0
    invalid = 0
    duplicates = 0
    seen_hashes: set[str] = set()
    errors: list[str] = []

    for p in sorted(extracted_dir.rglob("*")):
        if not p.is_file():
            continue
        total += 1
        ext = p.suffix.lower()
        if ext not in ALLOWED_IMAGE_EXTS:
            invalid += 1
            if len(errors) < 10:
                errors.append(f"Unsupported file: {p.name}")
            continue
        raw = p.read_bytes()
        arr = np.frombuffer(raw, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            invalid += 1
            if len(errors) < 10:
                errors.append(f"Corrupt/unreadable image: {p.name}")
            continue
        digest = hashlib.sha256(raw).hexdigest()
        if digest in seen_hashes:
            duplicates += 1
        else:
            seen_hashes.add(digest)
        valid += 1

    status = "Validated" if valid > 0 and invalid == 0 else "Validation failed"
    if valid == 0 and not errors:
        errors.append("No valid images found in uploaded dataset.")

    return {
        "file_count": total,
        "valid_image_count": valid,
        "invalid_file_count": invalid,
        "duplicate_count": duplicates,
        "validation_status": status,
        "errors": errors,
        "resolution": f"{TARGET_WIDTH}x{TARGET_HEIGHT} (480p)",
    }


@router.get("", response_model=list[DatasetOut])
def list_datasets(db: Session = Depends(get_db)) -> list[DatasetOut]:
    rows = db.scalars(select(DatasetRecord).order_by(DatasetRecord.created_at.desc())).all()
    return [_to_out(r) for r in rows]


@router.post("/upload", response_model=DatasetOut, status_code=201)
async def upload_dataset(
    name: str = Form(...),
    category: str = Form("normal"),
    industry: str = Form("General"),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> DatasetOut:
    cleaned_name = name.strip()
    if not cleaned_name:
        raise HTTPException(status_code=422, detail="Dataset name cannot be blank")
    if not files:
        raise HTTPException(status_code=422, detail="At least one file must be uploaded")

    settings = get_settings()
    raw_dir = settings.data_root / "datasets"
    train_root = settings.data_root / "training"
    raw_dir.mkdir(parents=True, exist_ok=True)
    train_root.mkdir(parents=True, exist_ok=True)

    run_uid = uuid.uuid4().hex[:10]
    extracted_dir = train_root / f"ds_{run_uid}"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    hasher = hashlib.sha256()
    source_names: list[str] = []
    archive_path_str = ""
    saved_archives: list[Path] = []

    try:
        zip_files = [f for f in files if (f.filename or "").lower().endswith(".zip")]
        if zip_files and len(files) > 1:
            raise HTTPException(
                status_code=422,
                detail="Upload either a single .zip archive or individual image files, not both.",
            )

        if zip_files:
            f = zip_files[0]
            fname = Path(f.filename or "dataset.zip").name
            source_names.append(fname)
            raw_bytes = await f.read()
            hasher.update(raw_bytes)
            archive_file = raw_dir / f"{run_uid}_{fname}"
            archive_file.write_bytes(raw_bytes)
            saved_archives.append(archive_file)
            archive_path_str = str(archive_file)
            val = _validate_and_extract_zip(archive_file, extracted_dir)
        else:
            seen_hashes: set[str] = set()
            valid = 0
            duplicates = 0
            for f in files:
                fname = Path(f.filename or f"img_{uuid.uuid4().hex[:6]}.png").name
                ext = Path(fname).suffix.lower()
                if ext not in ALLOWED_IMAGE_EXTS:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Non-image file '{fname}' is not allowed.",
                    )
                source_names.append(fname)
                raw_bytes = await f.read()
                hasher.update(raw_bytes)
                raw_copy = raw_dir / f"{run_uid}_{fname}"
                raw_copy.write_bytes(raw_bytes)
                saved_archives.append(raw_copy)
                if not archive_path_str:
                    archive_path_str = str(raw_dir)
                digest = hashlib.sha256(raw_bytes).hexdigest()
                if digest in seen_hashes:
                    duplicates += 1
                else:
                    seen_hashes.add(digest)
                try:
                    _resize_and_compress_480p(raw_bytes, extracted_dir / fname)
                    valid += 1
                except ValueError as exc:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Corrupt or unreadable image '{fname}': {exc}",
                    )
            val = {
                "file_count": valid,
                "valid_image_count": valid,
                "invalid_file_count": 0,
                "duplicate_count": duplicates,
                "validation_status": "Validated" if valid > 0 else "Validation failed",
                "errors": [],
                "resolution": f"{TARGET_WIDTH}x{TARGET_HEIGHT} (480p)",
            }
    except HTTPException:
        shutil.rmtree(extracted_dir, ignore_errors=True)
        for p in saved_archives:
            p.unlink(missing_ok=True)
        raise

    ds = DatasetRecord(
        name=cleaned_name,
        category=category,
        industry=industry.strip() or "General",
        source_filename=", ".join(source_names[:3]) + ("…" if len(source_names) > 3 else ""),
        archive_path=archive_path_str,
        extracted_path=str(extracted_dir),
        file_count=val["file_count"],
        valid_image_count=val["valid_image_count"],
        invalid_file_count=val["invalid_file_count"],
        duplicate_count=val["duplicate_count"],
        validation_status=val["validation_status"],
        validation_details_json={"errors": val["errors"], "resolution": val["resolution"]},
        sha256_hash=hasher.hexdigest(),
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return _to_out(ds)


@router.post("/{dataset_id}/validate", response_model=DatasetOut)
def revalidate_dataset(dataset_id: int, db: Session = Depends(get_db)) -> DatasetOut:
    ds = db.get(DatasetRecord, dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    extracted_dir = Path(ds.extracted_path)
    if not extracted_dir.is_dir():
        raise HTTPException(status_code=404, detail="Extracted dataset directory missing on disk")
    val = _validate_extracted_dir(extracted_dir)
    ds.file_count = val["file_count"]
    ds.valid_image_count = val["valid_image_count"]
    ds.invalid_file_count = val["invalid_file_count"]
    ds.duplicate_count = val["duplicate_count"]
    ds.validation_status = val["validation_status"]
    ds.validation_details_json = {"errors": val["errors"], "resolution": val["resolution"]}
    db.commit()
    db.refresh(ds)
    return _to_out(ds)


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    ds = db.get(DatasetRecord, dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    extracted = Path(ds.extracted_path)
    if extracted.is_dir():
        shutil.rmtree(extracted, ignore_errors=True)
    archive = Path(ds.archive_path)
    if archive.is_file():
        archive.unlink(missing_ok=True)
    db.delete(ds)
    db.commit()
    return {"status": "deleted", "id": str(dataset_id)}
