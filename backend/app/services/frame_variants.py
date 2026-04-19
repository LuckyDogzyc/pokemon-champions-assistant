from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FrameVariants:
    base_frame: dict[str, Any]
    phase_frame: dict[str, Any]
    roi_source_frame: dict[str, Any]


_FRAME_METADATA_KEYS = (
    'timestamp',
    'layout_variant',
    'layout_variant_hint',
    'annotation_target',
    'roi_candidates',
)


def resolve_frame_variants(frame: dict[str, Any]) -> FrameVariants:
    frame_variants = frame.get('frame_variants')
    if not isinstance(frame_variants, dict):
        return FrameVariants(base_frame=frame, phase_frame=frame, roi_source_frame=frame)

    phase_frame = _merge_frame_metadata(frame, frame_variants.get('phase_frame'))
    roi_source_frame = _merge_frame_metadata(frame, frame_variants.get('roi_source_frame'))
    return FrameVariants(
        base_frame=frame,
        phase_frame=phase_frame,
        roi_source_frame=roi_source_frame,
    )


def _merge_frame_metadata(base_frame: dict[str, Any], variant: Any) -> dict[str, Any]:
    if not isinstance(variant, dict):
        return base_frame

    merged = dict(base_frame)
    merged.update(variant)
    for key in _FRAME_METADATA_KEYS:
        if key not in merged and key in base_frame:
            merged[key] = base_frame[key]
    return merged
