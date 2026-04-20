export type RecognitionSource = 'ocr' | 'manual' | 'mock';
export type BattlePhase = 'team_select' | 'switching' | 'battle' | 'move_resolution' | 'unknown';

export interface VideoSource {
  id: string;
  label: string;
  backend?: string;
  is_capture_card_candidate?: boolean;
  is_selected?: boolean;
  device_index?: number | null;
  capture_selector?: string | null;
  device_kind?: 'physical' | 'virtual' | 'unknown' | string | null;
}

export interface VideoSourcesResponse {
  sources: VideoSource[];
}

export interface SelectVideoSourceResponse {
  selected_source_id: string;
}

export interface RoiDebugInfo {
  x: number;
  y: number;
  w: number;
  h: number;
  confidence?: string;
}

export interface RoiPayload {
  role?: string;
  source?: string;
  layout_variant?: string | null;
  recognized_texts?: string[];
  recognized_count?: number;
  matched_by?: string | null;
  preview_image_data_url?: string | null;
  pixel_box?: {
    left: number;
    top: number;
    width: number;
    height: number;
  };
  crop_width?: number;
  crop_height?: number;
  // Status panel fields
  pokemon_name?: string | null;
  hp_text?: string | null;
  hp_percentage?: string | null;
  level?: string | null;
  status_abnormality?: string | null;
  raw_texts?: string[];
  raw_count?: number;
  [key: string]: unknown;
}

export interface RecognizedSide {
  name?: string | null;
  confidence: number;
  source: RecognitionSource;
  debug_raw_text?: string | null;
  debug_roi?: RoiDebugInfo | null;
  matched_by?: string | null;
}

export interface TeamPreviewState {
  player_team: string[];
  opponent_team: string[];
  selected_count?: number | null;
  instruction_text?: string | null;
}

export interface FrameVariantDebugInfo {
  source?: string | null;
  width?: number | null;
  height?: number | null;
  preview_image_data_url?: string | null;
}

export interface RecognitionState {
  current_phase: BattlePhase;
  player: RecognizedSide;
  opponent: RecognizedSide;
  player_active_name?: string | null;
  opponent_active_name?: string | null;
  timestamp?: string;
  input_source?: string;
  layout_variant?: string | null;
  phase_evidence?: string[];
  roi_payloads?: Record<string, RoiPayload>;
  team_preview?: TeamPreviewState | null;
  preview_image_data_url?: string | null;
  capture_error?: string | null;
  capture_error_detail?: string | null;
  capture_method?: string | null;
  capture_backend?: string | null;
  frame_variants_debug?: Record<string, FrameVariantDebugInfo>;
  capture_help_text?: string | null;
  capture_suggested_source_id?: string | null;
  capture_suggested_source_label?: string | null;
  ocr_provider?: string | null;
  ocr_warning?: string | null;
}

export interface RecognitionSessionStartResponse {
  running: boolean;
  input_source?: string;
  current_state: RecognitionState;
}

export interface PokemonSearchResult {
  canonical_name: string;
  match_type?: string;
  pokemon?: {
    id: string;
    name_zh: string;
    types: string[];
  };
}

export interface PokemonSearchResponse {
  query: string;
  results: PokemonSearchResult[];
}
