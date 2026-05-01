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
  is_virtual?: boolean;
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
  // Team select slot fields
  item?: string | null;
  gender?: string | null;
  is_selected?: boolean;
  // Move slot fields
  pp_current?: number | null;
  pp_max?: number | null;
  [key: string]: unknown;
}

export interface RecognizedSide {
  name?: string | null;
  confidence: number;
  source: RecognitionSource;
  debug_raw_text?: string | null;
  debug_roi?: RoiDebugInfo | null;
  matched_by?: string | null;
  matched_pokemon_id?: string | null;
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

// ── Battle State Types ──

export type FieldCondition =
  | 'none' | 'sun' | 'rain' | 'sandstorm' | 'hail' | 'snow'
  | 'trick_room' | 'tailwind_player' | 'tailwind_opponent'
  | 'reflect_player' | 'reflect_opponent'
  | 'light_screen_player' | 'light_screen_opponent'
  | 'aurora_veil_player' | 'aurora_veil_opponent';

export type StatusCondition =
  | 'none' | 'burn' | 'poison' | 'bad_poison' | 'paralysis'
  | 'sleep' | 'freeze' | 'confusion' | 'flinch';

export interface StatStages {
  attack: number;
  defense: number;
  sp_attack: number;
  sp_defense: number;
  speed: number;
  accuracy: number;
  evasion: number;
}

export interface MonBattleState {
  pokemon_id: string | null;
  name: string | null;
  level: number;
  current_hp_percent: number | null;
  status: StatusCondition;
  stat_stages: StatStages;
  revealed_moves: string[];
  item_revealed: string | null;
  ability_revealed: string | null;
  turns_on_field: number;
}

export interface TeamEntry {
  pokemon_id: string | null;
  name: string | null;
  is_active: boolean;
  is_fainted: boolean;
  item: string | null;
  gender: string | null;
}

export interface BattleState {
  battle_id: string;
  turn: number;
  phase: string;
  field_conditions: FieldCondition[];
  player_active: MonBattleState;
  opponent_active: MonBattleState;
  player_team: TeamEntry[];
  opponent_team: TeamEntry[];
  move_log: Record<string, unknown>[];
  hp_history: Record<string, unknown>[];
}

// ── Moves Data ──

export interface MoveInfo {
  name: string;
  type: string;
  category: 'Physical' | 'Special' | 'Status';
  basePower: number;
  pp: number;
  priority: number;
  target: string;
}

// ── Base Stats ──

export interface BaseStats {
  hp: number;
  attack: number;
  defense: number;
  sp_attack: number;
  sp_defense: number;
  speed: number;
}

// ── Recognition State (main polling payload) ──

export interface RecognizedTeamSlot {
  name: string | null;
  item: string | null;
  gender: string | null;
  sprite_match_id: string | null;
  sprite_confidence: number;
  is_selected: boolean;
  debug_raw_text?: string | null;
  debug_roi?: RoiDebugInfo | null;
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
  recognition_error?: string | null;
  recognition_error_detail?: string | null;
  // Enriched from backend
  battle_state?: BattleState;
  player_base_stats?: BaseStats;
  opponent_base_stats?: BaseStats;
  // 全流程追踪 v2
  player_team_slots?: RecognizedTeamSlot[];
  opponent_team_slots?: RecognizedTeamSlot[];
  locked_in?: boolean;
  player_hp_current?: number | null;
  player_hp_max?: number | null;
  opponent_hp_percent?: number | null;
  revealed_moves?: Record<string, unknown>[];
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
