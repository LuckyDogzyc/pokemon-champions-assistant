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
  team_preview?: TeamPreviewState | null;
  preview_image_data_url?: string | null;
  capture_error?: string | null;
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
