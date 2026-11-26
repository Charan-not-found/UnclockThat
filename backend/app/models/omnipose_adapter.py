"""Pose-Agnostic Multi-View Anomaly Detection adapter (OmniPoseAD-style).

Trains a multi-view DINOv2 reference bank from normal images and aligns query
viewpoints via feature matching + homography before computing patch-level anomaly maps.
"""

from __future__ import annotations

import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Optional

import cv2
import numpy as np

from backend.app.core.config import BASE_DIR, get_settings


class OmniPoseAdapter:
    """Thread-safe trainer and predictor for pose-agnostic multi-view anomaly detection."""

    _lock = threading.Lock()
    _backbone: Any = None
    _banks: dict[str, dict[str, Any]] = {}

    @classmethod
    def _get_backbone(cls):
        import torch
        import timm

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
    def _extract_features(cls, bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return (global_embedding [D], patch_grid [H_p, W_p, D]) L2-normalized."""
        import torch
        import torch.nn.functional as F

        backbone, device = cls._get_backbone()
        rgb = cv2.cvtColor(cv2.resize(bgr, (518, 518), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).float().unsqueeze(0) / 255.0
        mean = torch.tensor([0.485, 0.456, 0.406], device=device).view(1, 3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225], device=device).view(1, 3, 1, 1)
        tensor = (tensor.to(device) - mean) / std

        with torch.no_grad():
            feats = backbone.forward_features(tensor)  # (1, 1 + reg + N_patches, D)
            cls_tok = F.normalize(feats[:, 0, :], dim=-1).squeeze(0).cpu().numpy()
            # DINOv2 reg4 has 1 cls + 4 register tokens = 5 prefix tokens; 518/14 = 37x37 = 1369 patches
            n_patches = 37 * 37
            patch_toks = feats[:, -n_patches:, :]
            patch_toks = F.normalize(patch_toks, dim=-1).squeeze(0).reshape(37, 37, -1).cpu().numpy()
        return cls_tok, patch_toks

    @classmethod
    def _align_to_reference(cls, query_bgr: np.ndarray, ref_bgr: np.ndarray) -> np.ndarray:
        """Align query image viewpoint to nearest reference view via ORB + RANSAC homography."""
        h, w = ref_bgr.shape[:2]
        q_resized = cv2.resize(query_bgr, (w, h), interpolation=cv2.INTER_AREA)

        orb = cv2.ORB_create(nfeatures=1000)
        kp1, des1 = orb.detectAndCompute(cv2.cvtColor(q_resized, cv2.COLOR_BGR2GRAY), None)
        kp2, des2 = orb.detectAndCompute(cv2.cvtColor(ref_bgr, cv2.COLOR_BGR2GRAY), None)
        if des1 is None or des2 is None or len(kp1) < 8 or len(kp2) < 8:
            return q_resized

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = sorted(bf.match(des1, des2), key=lambda m: m.distance)[:60]
        if len(matches) < 8:
            return q_resized

        src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
        H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        if H is None or mask is None or int(mask.sum()) < 6:
            return q_resized

        return cv2.warpPerspective(q_resized, H, (w, h), borderMode=cv2.BORDER_REPLICATE)

    @classmethod
    def fit_dataset(
        cls,
        dataset_dir: Path,
        out_path: Path,
        max_refs: int = 120,
        progress_cb: Optional[Callable[[int, str], None]] = None,
    ) -> dict[str, Any]:
        """Build a multi-view pose-agnostic reference bank from normal images."""
        import torch

        exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
        img_paths = [p for p in sorted(dataset_dir.rglob("*")) if p.is_file() and p.suffix.lower() in exts][:max_refs]
        if not img_paths:
            raise ValueError("No valid images found in dataset for OmniPoseAD.")

        global_embs = []
        patch_banks = []
        valid_paths = []

        for idx, p in enumerate(img_paths):
            bgr = cv2.imread(str(p))
            if bgr is None:
                continue
            g, patches = cls._extract_features(bgr)
            global_embs.append(g)
            patch_banks.append(patches.astype(np.float16))
            valid_paths.append(str(p))
            if progress_cb and (idx % 10 == 0 or idx == len(img_paths) - 1):
                pct = 25 + int(((idx + 1) / len(img_paths)) * 65)
                progress_cb(pct, f"Indexed reference view {idx + 1}/{len(img_paths)}")

        if not valid_paths:
            raise ValueError("Failed to extract features from any dataset image.")

        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "global_embeddings": np.stack(global_embs, axis=0).astype(np.float32),
            "patch_banks": np.stack(patch_banks, axis=0),  # (N, 37, 37, D) float16
            "ref_paths": valid_paths,
        }
        torch.save(payload, str(out_path))
        with cls._lock:
            cls._banks.pop(str(out_path.resolve()), None)

        return {
            "reference_views_indexed": len(valid_paths),
            "backbone": "vit_base_patch14_reg4_dinov2",
        }

    @classmethod
    def predict_bytes(
        cls,
        raw_bytes: bytes,
        bank_path: Path,
        threshold: float = 0.5,
    ) -> dict[str, Any]:
        """Match query to nearest reference viewpoint, pose-align, and compute anomaly map."""
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

        # Step 1: Retrieve nearest viewpoint in reference bank
        q_global, _ = cls._extract_features(bgr)
        sims = bank["global_embeddings"] @ q_global
        best_idx = int(np.argmax(sims))
        best_sim = float(sims[best_idx])

        # Step 2: Pose-align query to nearest reference view if file exists on disk
        ref_path = Path(bank["ref_paths"][best_idx])
        if ref_path.is_file():
            ref_bgr = cv2.imread(str(ref_path))
            aligned_bgr = cls._align_to_reference(bgr, ref_bgr) if ref_bgr is not None else bgr
        else:
            aligned_bgr = bgr

        # Step 3: Dense patch cosine distance against matched reference view
        _, q_patches = cls._extract_features(aligned_bgr)
        ref_patches = bank["patch_banks"][best_idx].astype(np.float32)
        cos_sim = np.sum(q_patches * ref_patches, axis=-1)  # (37, 37)
        diff_map = np.clip((1.0 - cos_sim) * 1.6, 0.0, 1.0)

        anomaly_score = round(float(np.percentile(diff_map, 97)), 4)
        amap_full = cv2.resize(diff_map.astype(np.float32), (w_orig, h_orig), interpolation=cv2.INTER_LINEAR)

        settings = get_settings()
        results_dir = settings.storage_root / "inspection_results"
        results_dir.mkdir(parents=True, exist_ok=True)
        heatmap_file = results_dir / f"{uuid.uuid4().hex}_omniposead_heatmap.png"

        heat_uint8 = np.uint8(np.clip(amap_full * 255.0, 0, 255))
        heat_color = cv2.applyColorMap(heat_uint8, cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(bgr, 0.6, heat_color, 0.4, 0)
        cv2.imwrite(str(heatmap_file), overlay)

        out_vis_dir = BASE_DIR / "outputs" / "visualizations"
        out_vis_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_vis_dir / heatmap_file.name), overlay)

        defects: list[dict[str, Any]] = []
        if anomaly_score >= threshold:
            mask = np.uint8(amap_full >= max(0.5, threshold)) * 255
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            total_area = max(1, h_orig * w_orig)
            for cnt in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
                area = cv2.contourArea(cnt)
                if area / total_area < 0.002:
                    continue
                x, y, w, h = cv2.boundingRect(cnt)
                region_peak = float(amap_full[y : y + h, x : x + w].max()) if w > 0 and h > 0 else anomaly_score
                defects.append({
                    "type": "Pose-Aligned Anomaly (OmniPoseAD)",
                    "severity": (
                        "Critical" if anomaly_score >= 0.85
                        else "Major" if anomaly_score >= 0.65
                        else "Minor"
                    ),
                    "confidence": round(min(0.99, 0.55 + best_sim * 0.4), 3),
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
            "confidence_score": round(min(0.99, max(0.5, best_sim)), 3),
            "defects": defects,
            "heatmap_path": str(heatmap_file),
            "processing_time_ms": elapsed_ms,
            "model_name": "OmniPoseAD (Pose-Agnostic)",
        }
