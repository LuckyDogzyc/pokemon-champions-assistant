# Changelog

All notable changes to this project will be documented in this file.

## [v0.1.33] - 2026-04-23

### Changed
- Changed the Windows portable launcher to force `PADDLE_OCR_BASE_DIR` to the bundled `.paddleocr` directory before starting the backend, so packaged builds prefer in-bundle OCR assets instead of the user profile cache or any pre-existing environment override.
- Changed the PaddleOCR adapter to lazy-load `paddleocr` at runtime and normalize unexpected bootstrap failures into `ImportError`, allowing the recognition runtime to surface a controlled fallback warning instead of crashing the backend import path.
- Changed release asset preparation to use an explicit `bootstrap_paddleocr_assets.py` helper with pinned model URLs, SHA-256 verification, and safe tar-member validation instead of an implicit `PaddleOCR(...)` bootstrap side effect.

### Fixed
- Fixed Windows portable startup crashes caused by missing `Cython/Utility/CppSupport.cpp` in the PyInstaller bundle by explicitly collecting Cython data files.
- Fixed Windows portable OCR packaging so the build step prepares the required Chinese det/rec/cls PaddleOCR models into a bundle-local `.paddleocr` directory and ships that directory inside the release ZIP.
- Fixed release verification smoke tests to prewarm bundled OCR assets before launcher startup, avoiding first-boot model downloads during the healthcheck window.
- Added release regressions that lock the bundled OCR-model bootstrap path, bundled `.paddleocr` asset inclusion, launcher-side `PADDLE_OCR_BASE_DIR` override behavior, checksum-pinned model bootstrap, safe archive extraction, and lazy PaddleOCR import behavior.

### Testing
- Backend: `python3 -m pytest backend/tests/test_bootstrap_paddleocr_assets.py backend/tests/test_release_runtime.py backend/tests/test_release_frontend_server.py backend/tests/test_release_frozen_runtime.py backend/tests/test_verify_release_script.py backend/tests/test_windows_packaging_script.py backend/tests/test_recognition_runtime.py backend/tests/test_paddle_ocr_adapter.py -q` → 27 passed.
- Release verification: `python3 release/scripts/verify_release.py --skip-frontend-tests --skip-frontend-build` → passed.

## [v0.1.29] - 2026-04-21

### Changed
- Changed the default OCR provider from `mock` to `paddleocr`, so environments with PaddleOCR installed now enter the real OCR path by default while still keeping automatic fallback-to-mock behavior when PaddleOCR is unavailable.
- Changed battle ROI contracts, fixtures, and the frontend debug panel to keep only `player_status_panel`, `opponent_status_panel`, and `move_list` for battle-page validation, removing unused `player_name`, `opponent_name`, and `command_panel` cards from the battle debug chain.
- Changed the `battle_move_menu_open` `move_list` ROI anchor to a smaller lower-right crop so move-list previews focus on the 4 actual moves instead of overlapping the upper command area.

### Fixed
- Fixed the mismatch where a local environment with PaddleOCR installed could still appear as `mock` OCR in the runtime/debug state because the default provider setting had not been switched over.
- Fixed battle debug/sample expectations so the Gallade move-list regression locks all 4 moves while keeping order temporarily insensitive under the new minimal ROI layout.
- Fixed README OCR-provider examples and wording so release/runtime docs match the actual default behavior.

### Testing
- Backend: `python3 -m pytest backend/tests/test_settings.py backend/tests/test_recognition_runtime.py backend/tests/test_layout_templates.py backend/tests/test_battle_roi_annotation_samples.py backend/tests/test_recognition_api.py backend/tests/test_real_ocr_battle_samples.py backend/tests/test_paddle_ocr_adapter.py -q` → 20 passed, 1 skipped.
- Frontend: `cd frontend && npx jest --runInBand tests/debug-panel-battle-rois.test.tsx tests/hooks.test.ts` → passed.

## [v0.1.28] - 2026-04-20

### Added
- Added runtime OCR provider selection with explicit `ocr_provider` / `ocr_warning` debug fields so operators can tell whether the app is using PaddleOCR or has fallen back to mock OCR.
- Added real-sample battle regressions for status-panel parsing, move-list locking, and PaddleOCR ROI handling, including protection against double-cropping already prepared ROI frames.

### Changed
- Changed battle ROI anchors and debug output so battle screens expose `player_status_panel`, `opponent_status_panel`, and `move_list` more reliably for fast manual validation.
- Changed battle move-list acceptance to lock exactly 4 moves while keeping order temporarily insensitive, and preserve observed OCR text such as `三旋击` instead of forcing canonical-name normalization.
- Changed the frontend polling hook to start the recognition session on first load, so the latest captured screenshot can appear immediately beside the video source workflow.

### Fixed
- Fixed recognition API guidance for capture-device contention so OBS Virtual Camera is suggested when the capture card is busy.
- Fixed PaddleOCR ROI reading so pre-cropped ROI frames are consumed directly instead of being cropped a second time.
- Fixed stale docs that still described the old 3-second recognition cadence; the documented default now matches the implemented 1-second polling/capture interval.

### Testing
- Backend: `python3 -m pytest backend/tests/test_battle_roi_annotation_samples.py backend/tests/test_chinese_ocr_recognizer.py backend/tests/test_real_ocr_battle_samples.py backend/tests/test_recognition_pipeline_enhanced.py backend/tests/test_recognition_api.py backend/tests/test_capture_session.py backend/tests/test_settings.py backend/tests/test_recognition_runtime.py backend/tests/test_paddle_ocr_adapter.py -q` → 48 passed, 1 skipped.
- Frontend: `cd frontend && npx jest --runInBand tests/debug-panel-battle-rois.test.tsx tests/hooks.test.ts` → 2 suites passed.

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
