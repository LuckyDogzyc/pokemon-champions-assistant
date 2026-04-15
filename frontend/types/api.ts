export type RecognitionSource = 'ocr' | 'manual' | 'mock';
export type BattlePhase = 'team_select' | 'switching' | 'battle' | 'move_resolution' | 'unknown';

export interface VideoSource {
  id: string;
  label: string;
  backend?: string;
  is_capture_card_candidate?: boolean;
  is_selected?: boolean;
}

export interface VideoSourcesResponse {
  sources: VideoSource[];
}

export interface SelectVideoSourceResponse {
  selected_source_id: string;
}

export interface RecognizedSide {
  name?: string | null;
  confidence: number;
  source: RecognitionSource;
}

export interface RecognitionState {
  current_phase: BattlePhase;
  player: RecognizedSide;
  opponent: RecognizedSide;
  player_active_name?: string | null;
  opponent_active_name?: string | null;
  timestamp?: string;
  input_source?: string;
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
