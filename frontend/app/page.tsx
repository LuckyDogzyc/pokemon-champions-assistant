'use client';

import { useRef, useState, useMemo } from 'react';

import type { MoveInfo } from '../types/api';
import { BattleInfoPanel } from '../components/battle-info-panel';
import { DebugInfoPanel } from '../components/debug-info-panel';
import { GameScreenPanel } from '../components/game-screen-panel';
import { MovePanel } from '../components/move-panel';
import { TeamRosterPanel } from '../components/team-roster-panel';
import { TopBar } from '../components/top-bar';
import { useRecognitionPolling, useVideoSources } from '../lib/hooks';
import { searchMoves } from '../lib/api';
import type { BaseStats, BattleState, MonBattleState, TeamEntry } from '../types/api';

// ── Default empty battle state ──

const EMPTY_MON: MonBattleState = {
  pokemon_id: null,
  name: null,
  level: 50,
  current_hp_percent: null,
  status: 'none',
  stat_stages: { attack: 0, defense: 0, sp_attack: 0, sp_defense: 0, speed: 0, accuracy: 0, evasion: 0 },
  revealed_moves: [],
  item_revealed: null,
  ability_revealed: null,
  turns_on_field: 0,
};

function emptyBattleState(): BattleState {
  return {
    battle_id: '',
    turn: 0,
    phase: 'unknown',
    field_conditions: [],
    player_active: { ...EMPTY_MON },
    opponent_active: { ...EMPTY_MON },
    player_team: [],
    opponent_team: [],
    move_log: [],
    hp_history: [],
  };
}

// ── Move lookup helper ──

function buildMoveEntries(
  moveNames: string[],
  movesCache: Record<string, MoveInfo>,
): { name: string; type: string; category: 'Physical' | 'Special' | 'Status'; basePower: number; pp: number; currentPp: number }[] {
  return moveNames.map((name) => {
    const info = movesCache[name];
    return {
      name,
      type: info?.type ?? 'Normal',
      category: info?.category ?? 'Physical',
      basePower: info?.basePower ?? 0,
      pp: info?.pp ?? 15,
      currentPp: info?.pp ?? 15,
    };
  });
}

// ── Main page ──

export default function HomePage() {
  const { sources, selectSource } = useVideoSources();
  const { state, restartSession } = useRecognitionPolling(2000);
  const sourceSelectionInFlightRef = useRef<Promise<void> | null>(null);
  const [debugOpen, setDebugOpen] = useState(false);
  const [movesCache, setMovesCache] = useState<Record<string, MoveInfo>>({});

  // Extract battle state
  const battle: BattleState = state?.battle_state ?? emptyBattleState();
  const playerBaseStats: BaseStats | null = state?.player_base_stats ?? null;
  const opponentBaseStats: BaseStats | null = state?.opponent_base_stats ?? null;

  // Current video source
  const selectedSourceId = sources.find(s => s.is_selected)?.id ?? sources[0]?.id ?? '';

  // Load move info on demand
  const playerMoveEntries = useMemo(() => {
    const names = battle.player_active.revealed_moves;
    if (names.length === 0) return [];
    // Kick off async lookup for any uncached moves
    const uncached = names.filter(n => !movesCache[n]);
    if (uncached.length > 0) {
      searchMoves(uncached.join(',')).then((result) => {
        const updates = result.moves ?? {};
        setMovesCache(prev => ({ ...prev, ...updates }));
      }).catch(() => {});
    }
    return buildMoveEntries(names, movesCache);
  }, [battle.player_active.revealed_moves, movesCache]);

  // Source selection handler
  const handleSelectSource = async (sourceId: string) => {
    if (sourceSelectionInFlightRef.current) {
      return sourceSelectionInFlightRef.current;
    }
    const pending = (async () => {
      await selectSource(sourceId);
      await restartSession();
    })().finally(() => {
      if (sourceSelectionInFlightRef.current === pending) {
        sourceSelectionInFlightRef.current = null;
      }
    });
    sourceSelectionInFlightRef.current = pending;
    return pending;
  };

  // Get player/opponent types from base stats name if available
  // For now, derive from recognition state names
  const playerTypes: string[] = [];
  const opponentTypes: string[] = [];

  return (
    <main className="app-layout">
      {/* Top bar: source + debug */}
      <TopBar
        sources={sources}
        selectedSourceId={selectedSourceId}
        debugOpen={debugOpen}
        onToggleDebug={() => setDebugOpen(d => !d)}
        onSelectSource={handleSelectSource}
      />

      {/* Debug panel (collapsible, below top bar) */}
      {debugOpen && (
        <div className="debug-section">
          <DebugInfoPanel state={state ?? null} />
        </div>
      )}

      {/* Main content: 5-column layout */}
      <div className="main-content">
        {/* Left outer: Player team roster */}
        <div className="col-left-outer">
          <TeamRosterPanel side="player" team={battle.player_team} />
        </div>

        {/* Left inner: Player battle info */}
        <div className="col-left-inner">
          <BattleInfoPanel
            side="player"
            mon={battle.player_active}
            baseStats={playerBaseStats}
            opponentBaseStats={opponentBaseStats}
            opponentMon={battle.opponent_active}
            level={battle.player_active.level || 50}
          />
          <MovePanel
            moves={playerMoveEntries}
            attackerStats={playerBaseStats ?? { hp: 0, attack: 0, defense: 0, sp_attack: 0, sp_defense: 0, speed: 0 }}
            attackerStages={battle.player_active.stat_stages}
            defenderStats={opponentBaseStats ?? { hp: 0, attack: 0, defense: 0, sp_attack: 0, sp_defense: 0, speed: 0 }}
            defenderStages={battle.opponent_active.stat_stages}
            defenderHpPercent={battle.opponent_active.current_hp_percent ?? 100}
            attackerTypes={playerTypes}
            defenderTypes={opponentTypes}
          />
        </div>

        {/* Center: Game screen */}
        <div className="col-center">
          <GameScreenPanel
            previewImageDataUrl={state?.preview_image_data_url ?? null}
            phase={state?.current_phase ?? null}
          />
        </div>

        {/* Right inner: Opponent battle info */}
        <div className="col-right-inner">
          <BattleInfoPanel
            side="opponent"
            mon={battle.opponent_active}
            baseStats={opponentBaseStats}
            opponentBaseStats={playerBaseStats}
            opponentMon={battle.player_active}
            level={battle.opponent_active.level || 50}
          />
        </div>

        {/* Right outer: Opponent team roster */}
        <div className="col-right-outer">
          <TeamRosterPanel side="opponent" team={battle.opponent_team} />
        </div>
      </div>

      {/* Field conditions bar */}
      {battle.field_conditions.length > 0 && (
        <div className="field-bar">
          {battle.field_conditions.map((fc) => (
            <span key={fc} className="field-tag">{fc}</span>
          ))}
        </div>
      )}
    </main>
  );
}
