"""AnomalyDINO (Damm et al., WACV 2025) custom model adapter.

Implements:
  1. Frozen DINOv2 ViT-B/14 patch feature extraction (L2-normalized).
  2. Few-shot 4-way rotation augmentation (when <= 16 normal reference images).
  3. PCA PC1 foreground/background patch masking (auto-enabled for object-centric data).
  4. Cosine-distance deep nearest-neighbor search against the normal patch memory bank.
  5. Mean top-1% (Tail Value at Risk) image-level anomaly score aggregation.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Optional

import cv2
import numpy as np

from backend.app.core.config import BASE_DIR, get_settings


class AnomalyDINOAdapter:
    """Thread-safe few-shot / patch-based AnomalyDINO trainer and predictor."""

    _lock = threading.Lock()
    _backbone: Any = None
    _banks: dict[str, dict[str, Any]] = {}

    @classmethod
    def _get_backbone(cls):
        import timm
        import torch

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        with cls._lock:
            if cls._backbone is None:
                model = timm.create_model(
                    "vit_base_patch14_reg4_dinov2",
                    pretrained=True,
                    num_classes=0,
                )
                model.to(device)
                model.eval()
                cls._backbone = model
        return cls._backbone, device

    @classmethod
    def _extract_patches(cls, bgr: np.ndarray) -> np.ndarray:
        """Extract L2-normalized DINOv2 patch tokens of shape (1369, D) for a 37x37 grid."""
        import torch
        import torch.nn.functional as F

        backbone, device = cls._get_backbone()
        rgb = cv2.cvtColor(cv2.resize(bgr, (518, 518), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).float().unsqueeze(0) / 255.0
        mean = torch.tensor([0.485, 0.456, 0.406], device=device).view(1, 3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225], device=device).view(1, 3, 1, 1)
        tensor = (tensor.to(device) - mean) / std

        with torch.no_grad():
            feats = backbone.forward_features(tensor)  # (1, 1 + 4 + 1369, D)
            n_patches = 37 * 37
            patch_toks = feats[:, -n_patches:, :]
            patch_toks = F.normalize(patch_toks, dim=-1).squeeze(0).cpu().numpy()
        return patch_toks.astype(np.float32)

    @staticmethod
    def _fit_pca_mask(all_patches: np.ndarray) -> tuple[np.ndarray, np.ndarray, bool]:
        """Fit PC1 on normal patches to separate object foreground from background."""
        sample = all_patches
        if len(sample) > 8192:
            step = max(1, len(sample) // 8192)
            sample = sample[::step][:8192]

        mean_vec = sample.mean(axis=0, keepdims=True)
        centered = sample - mean_vec
        _, _, vt = np.linalg.svd(centered, full_matrices=False)
        pc1_dir = vt[0].astype(np.float32)

        # Orient pc1_dir so center patches of a 37x37 grid tend to be positive (foreground)
        first_img_grid = all_patches[: 37 * 37].reshape(37, 37, -1)
        center_proj = float(((first_img_grid[10:27, 10:27, :] - mean_vec) @ pc1_dir).mean())
        border_proj = float(((first_img_grid[:5, :5, :] - mean_vec) @ pc1_dir).mean())
        if center_proj < border_proj:
            pc1_dir = -pc1_dir

        proj = (sample - mean_vec) @ pc1_dir
        fg_ratio = float((proj > 0.0).mean())
        # Only enable masking when a genuine foreground/background split exists
        use_masking = 0.15 <= fg_ratio <= 0.85
        return mean_vec.squeeze(0).astype(np.float32), pc1_dir, use_masking

    @classmethod
    def fit_dataset(
        cls,
        dataset_dir: Path,
        out_path: Path,
        max_images: int = 120,
        max_bank_patches: int = 25000,
        progress_cb: Optional[Callable[[int, str], None]] = None,
    ) -> dict[str, Any]:
        """Build an AnomalyDINO patch memory bank with few-shot augmentation and PCA masking."""
        import torch

        exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
        img_paths = [p for p in sorted(dataset_dir.rglob("*")) if p.is_file() and p.suffix.lower() in exts][:max_images]
        if not img_paths:
            raise ValueError("No valid images found in dataset for AnomalyDINO.")

        few_shot_aug = len(img_paths) <= 16
        patch_chunks: list[np.ndarray] = []
        processed_views = 0

        for idx, p in enumerate(img_paths):
            bgr = cv2.imread(str(p))
            if bgr is None:
                continue
            views = [bgr]
            if few_shot_aug:
                views.append(cv2.rotate(bgr, cv2.ROTATE_90_CLOCKWISE))
                views.append(cv2.rotate(bgr, cv2.ROTATE_180))
                views.append(cv2.rotate(bgr, cv2.ROTATE_90_COUNTERCLOCKWISE))

            for v in views:
                patch_chunks.append(cls._extract_patches(v))
                processed_views += 1

            if progress_cb and (idx % 5 == 0 or idx == len(img_paths) - 1):
                pct = 25 + int(((idx + 1) / len(img_paths)) * 55)
                progress_cb(pct, f"Extracted AnomalyDINO patches ({idx + 1}/{len(img_paths)} images)")

        if not patch_chunks:
            raise ValueError("Failed to extract DINOv2 patch features from dataset images.")

        all_patches = np.concatenate(patch_chunks, axis=0)
        if progress_cb:
            progress_cb(85, "Fitting PCA foreground mask & coreset memory bank...")

        pc1_mean, pc1_dir, use_masking = cls._fit_pca_mask(all_patches)
        if use_masking:
            fg_mask = ((all_patches - pc1_mean) @ pc1_dir) > 0.0
            bank_patches = all_patches[fg_mask]
            if len(bank_patches) < 64:
                bank_patches = all_patches
                use_masking = False
        else:
            bank_patches = all_patches

        if len(bank_patches) > max_bank_patches:
            indices = np.linspace(0, len(bank_patches) - 1, max_bank_patches, dtype=np.int64)
            bank_patches = bank_patches[indices]

        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_bank": bank_patches.astype(np.float16),
            "pc1_mean": pc1_mean,
            "pc1_dir": pc1_dir,
            "use_masking": bool(use_masking),
            "few_shot_augmented": bool(few_shot_aug),
            "source_images": len(img_paths),
            "views_indexed": processed_views,
        }
        torch.save(payload, str(out_path))
        with cls._lock:
            cls._banks.pop(str(out_path.resolve()), None)

        return {
            "source_images": len(img_paths),
            "views_indexed": processed_views,
            "memory_bank_patches": int(len(bank_patches)),
            "pca_masking_enabled": bool(use_masking),
            "few_shot_augmented": bool(few_shot_aug),
            "backbone": "vit_base_patch14_reg4_dinov2",
        }

    @classmethod
    def predict_bytes(
        cls,
        raw_bytes: bytes,
        bank_path: Path,
        threshold: float = 0.5,
    ) -> dict[str, Any]:
        """Run cosine-NN patch search + mean top-1% aggregation on an uploaded image."""
        import torch

        t0 = time.perf_counter()
        key = str(bank_path.resolve())
        with cls._lock:
            bank = cls._banks.get(key)
            if bank is None:
                bank = torch.load(str(bank_path), map_location="cpu", weights_only=False)
                cls._banks[key] = bank

        arr = np.frombuffer(raw_bytes, dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            raise ValueError("Unable to decode uploaded image bytes")
        h_orig, w_orig = bgr.shape[:2]

        q_patches = cls._extract_patches(bgr)  # (1369, D)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        mem_np = bank["memory_bank"].astype(np.float32)
        q_t = torch.from_numpy(q_patches).to(device)
        m_t = torch.from_numpy(mem_np).to(device)

        with torch.no_grad():
            # Compute max cosine similarity to memory bank in chunks to keep VRAM low
            max_sim = torch.full((q_t.shape[0],), -1.0, device=device)
            chunk = 4096
            for start in range(0, m_t.shape[0], chunk):
                sims = q_t @ m_t[start : start + chunk].T
                chunk_max, _ = sims.max(dim=1)
                max_sim = torch.maximum(max_sim, chunk_max)
            patch_dists = (1.0 - max_sim).clamp(min=0.0).cpu().numpy()

        active_mask = np.ones(len(patch_dists), dtype=bool)
        if bank.get("use_masking", False):
            proj = (q_patches - bank["pc1_mean"]) @ bank["pc1_dir"]
            fg = proj > 0.0
            if int(fg.sum()) >= 16:
                active_mask = fg
                patch_dists = np.where(active_mask, patch_dists, 0.0)

        active_dists = patch_dists[active_mask]
        top_k = max(1, math.ceil(0.01 * len(active_dists)))
        top_vals = np.sort(active_dists)[-top_k:]
        raw_tvar = float(top_vals.mean())

        # Calibrated mapping from cosine distance [~0.08..0.55] -> [0..1]
        anomaly_score = round(float(np.clip((raw_tvar - 0.10) / 0.45, 0.0, 1.0)), 4)

        patch_map = np.clip((patch_dists.reshape(37, 37) - 0.10) / 0.45, 0.0, 1.0).astype(np.float32)
        patch_map = cv2.GaussianBlur(patch_map, (5, 5), sigmaX=1.2)
        amap_full = cv2.resize(patch_map, (w_orig, h_orig), interpolation=cv2.INTER_LINEAR)

        settings = get_settings()
        results_dir = settings.storage_root / "inspection_results"
        results_dir.mkdir(parents=True, exist_ok=True)
        heatmap_file = results_dir / f"{uuid.uuid4().hex}_anomalydino_heatmap.png"

        heat_uint8 = np.uint8(np.clip(amap_full * 255.0, 0, 255))
        heat_color = cv2.applyColorMap(heat_uint8, cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(bgr, 0.6, heat_color, 0.4, 0)
        cv2.imwrite(str(heatmap_file), overlay)

        out_vis_dir = BASE_DIR / "outputs" / "visualizations"
        out_vis_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_vis_dir / heatmap_file.name), overlay)

        defects: list[dict[str, Any]] = []
        if anomaly_score >= threshold:
            mask = np.uint8(amap_full >= max(0.45, threshold)) * 255
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            total_area = max(1, h_orig * w_orig)
            for cnt in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
                area = cv2.contourArea(cnt)
                if area / total_area < 0.002:
                    continue
                x, y, w, h = cv2.boundingRect(cnt)
                region_peak = float(amap_full[y : y + h, x : x + w].max()) if w > 0 and h > 0 else anomaly_score
                defects.append({
                    "type": "Patch Anomaly (AnomalyDINO)",
                    "severity": (
                        "Critical" if anomaly_score >= 0.85
                        else "Major" if anomaly_score >= 0.65
                        else "Minor"
                    ),
                    "confidence": round(min(0.99, 0.6 + anomaly_score * 0.35), 3),
                    "anomalyScore": round(max(anomaly_score, region_peak), 3),
                    "box": {
                        "x": int(x / w_orig * 100),
                        "y": int(y / h_orig * 100),
                        "w": max(4, int(w / w_orig * 100)),
                        "h": max(4, int(h / h_orig * 100)),
                    },
                })

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return {
            "anomaly_score": anomaly_score,
            "confidence_score": round(min(0.99, 0.72 + abs(anomaly_score - 0.5) * 0.45), 3),
            "defects": defects,
            "heatmap_path": str(heatmap_file),
            "processing_time_ms": elapsed_ms,
            "model_name": "AnomalyDINO (DINOv2 Few-Shot)",
        }
