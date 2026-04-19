# Changelog

All notable changes to this project will be documented in this file.

## [v0.1.27] - 2026-04-19

### Fixed
- Fixed the battle debug pipeline so a successfully captured frame can still expose battle ROI previews even when the phase detector returns `unknown`.
- Fixed `layout_variant` fallback in unknown-phase capture scenarios by defaulting visible battle screens to `battle_move_menu_open`, enabling left-bottom / top-right / right-side ROI splitting for manual validation.
- Added a backend regression test covering unknown-phase battle screenshots to ensure `player_status_panel`, `opponent_status_panel`, and `move_list` ROI previews are still generated.

### Testing
- Backend: `python3 -m pytest backend/tests/test_recognition_pipeline_enhanced.py backend/tests/test_recognition_api.py -q` → 15 passed.
- Frontend: `cd frontend && npx jest --runInBand tests/debug-panel-battle-rois.test.tsx tests/debug-panel-status-panel.test.tsx tests/debug-panel.test.tsx` → 3 suites passed.

## [v0.1.26] - 2026-04-19

### Added
- Added battle-focused debug panel coverage with explicit summaries for the player status block, opponent status block, and move list block.
- Added a dedicated frontend regression test for battle ROI debug rendering.

### Changed
- Changed phase-first recognition so battle screens can be detected from `phase_frame` OCR evidence even when no `layout_hint` is supplied.
- Changed layout inference to automatically classify `COMMAND + 招式说明` overlays as `battle_move_menu_open`, allowing battle ROI extraction to start from the captured frame alone.
- Changed the debug panel to surface battle ROI summaries in a more operator-friendly format for quick manual validation.

### Testing
- Backend: `python3 -m pytest backend/tests/test_recognition_pipeline_enhanced.py backend/tests/test_recognition_api.py -q` → 14 passed.
- Frontend: `npx jest --runInBand tests/debug-panel-battle-rois.test.tsx tests/debug-panel-status-panel.test.tsx tests/debug-panel.test.tsx` → 3 suites passed.

## [v0.1.25] - 2026-04-19

### Fixed
- Fixed Windows release verification so ROI crop previews can still be generated when `ffmpeg` is unavailable, by falling back to `cv2`-based image decoding/cropping/encoding.
- Added a regression test covering ROI preview cropping when `ffmpeg` is missing but OpenCV is available.

### Testing
- Backend: `python3 -m pytest backend/tests -q` → 101 passed.
- Release verification: `python release/scripts/verify_release.py --skip-frontend-tests --skip-frontend-build` → passed.

## [v0.1.24] - 2026-04-19

### Added
- Added structured OCR parsing for battle status panels, including Pokémon name, HP fraction, HP percentage, level, and common status ailments.
- Added ROI enrichment for `player_status_panel` and `opponent_status_panel` so structured status data now flows through the recognition pipeline.
- Added `frame_variants` support with explicit `phase_frame` and `roi_source_frame` semantics for the phase-first pipeline.
- Added debug visibility for frame variants so the recognition API and frontend debug panel can show frame source, dimensions, and preview data.
- Added phase detector sample-fixture indexing and parameterized regression coverage via `data/annotations/samples/index.json`.
- Added `data/annotations/samples/README.md` to document how real phase detector sample fixtures should be extended.
- Added Champions data update scripts and current/backed-up data snapshots to support future matchup/database workflows.

### Changed
- Changed Windows virtual camera routing so OBS Virtual Camera is treated as an OpenCV capture source instead of being misrouted through DirectShow.
- Changed product defaults and UI guidance to converge on an OBS Virtual Camera-first workflow.
- Changed video source recommendation logic to prefer `OBS Virtual Camera`, then other virtual devices, before physical capture-card candidates.
- Changed the frontend home page to poll recognition every 1 second instead of inheriting the previous 3 second default.
- Changed the OpenCV capture path to emit a lightweight downscaled `phase_frame` preview while preserving a higher-fidelity `roi_source_frame` for ROI work.
- Changed phase detector sample tests from hard-coded cases to indexed, parameterized fixture-based regression coverage.

### Fixed
- Fixed `_read_with_opencv` success payloads so they consistently include `capture_backend`.
- Fixed frontend debug output so status-panel OCR results render in a structured, readable way rather than as raw text blobs.
- Fixed OBS-first UI copy and recommendation behavior across dashboard, video source panel, and debug-related tests.
- Fixed the recognition startup flow so the home page immediately uses a 1 second polling interval aligned with the product messaging.

### Testing
- Backend: `python3 -m pytest backend/tests -q` → 100 passed.
- Frontend: `npx jest --no-coverage` → 8 suites passed, 13 tests passed.

## [v0.1.23] - 2026-04-19

### Fixed
- Retried DirectShow capture using probed FFmpeg video size and framerate options to improve Windows capture reliability.
