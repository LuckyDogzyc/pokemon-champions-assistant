'use client';

import { useCallback, useMemo, useRef, useState } from 'react';

import type {
  BattleMon, BattleSession, LogEntry,
  MoveInfo, RecognitionState, RoiPayload,
} from '../types/api';
import { DebugInfoPanel } from '../components/debug-info-panel';
import { TopBar } from '../components/top-bar';
import { useRecognitionPolling, useVideoSources } from '../lib/hooks';
import { searchMoves } from '../lib/api';

// ── Helpers ──

type MoveEntry = {
  name: string;
  type: string;
  category: 'Physical' | 'Special' | 'Status';
  basePower: number;
  pp: number;
  currentPp: number;
};

const TYPE_COLORS: Record<string, string> = {
  Normal: '#A8A878', Fire: '#F08030', Water: '#6890F0', Electric: '#F8D030',
  Grass: '#78C850', Ice: '#98D8D8', Fighting: '#C03028', Poison: '#A040A0',
  Ground: '#E0C068', Flying: '#A890F0', Psychic: '#F85888', Bug: '#A8B820',
  Rock: '#B8A038', Ghost: '#705898', Dragon: '#7038F8', Dark: '#705848',
  Steel: '#B8B8D0', Fairy: '#EE99AC',
};

function catIcon(cat: string): string {
  if (cat === 'Physical') return '⚔️';
  if (cat === 'Special') return '🔮';
  return '✦';
}

// ── Sub-components ──

function TeamSlots({ team }: { team: BattleMon[] }) {
  const slots = [];
  for (let i = 0; i < 6; i++) {
    const mon = team[i] ?? null;
    const name = mon?.name ?? null;
    slots.push(
      <div key={i} className={'team-slot' + (mon?.name ? '' : ' empty')}>
        <span className="team-slot-name">{name ?? '空位 ' + (i + 1)}</span>
        {mon?.item && <span className="team-slot-item">{mon.item}</span>}
        {mon?.gender && <span className="team-slot-gender">{mon.gender}</span>}
      </div>,
    );
  }
  return <div className="team-grid">{slots}</div>;
}

function PokeCard({
  mon,
}: {
  mon: BattleMon | null;
}) {
  if (!mon) {
    return (
      <div className="poke-card empty">
        <div className="empty-state">
          <span>🐾</span>
          <p>等待出场</p>
        </div>
      </div>
    );
  }

  const hp = mon.current_hp_percent ?? 100;
  const hpColor = hp > 50 ? '#4ade80' : hp > 20 ? '#fb923c' : '#f87171';
  const hpText = mon.current_hp != null && mon.max_hp != null
    ? mon.current_hp + '/' + mon.max_hp + ' ' + hp + '%'
    : (mon.current_hp_percent != null ? Math.round(mon.current_hp_percent) + '%' : null);
  const bs = mon.base_stats;

  return (
    <div className="poke-card">
      <div className="poke-header">
        <span className="poke-name">{mon.name ?? '???'}</span>
        {mon.gender && <span className="poke-gender">{mon.gender}</span>}
        {mon.item && <span className="poke-item">{mon.item}</span>}
        <span className="poke-level">Lv.{mon.level}</span>
      </div>

      {mon.status.length > 0 && (
        <div className="status-badge">{mon.status.join(', ')}</div>
      )}

      <div className="hp-row">
        <div className="hp-bar-bg">
          <div className="hp-bar-fill" style={{ width: Math.max(0, Math.min(100, hp)) + '%', backgroundColor: hpColor }} />
        </div>
        <span className="hp-text">{hpText ?? Math.round(hp) + '%'}</span>
      </div>

      {/* Base stats grid */}
      {Object.keys(bs).length > 0 && (
        <div className="stats-mini">
          {['hp', 'attack', 'defense', 'sp_attack', 'sp_defense', 'speed'].map(s => {
            const labels: Record<string, string> = {
              hp: 'HP', attack: '物攻', defense: '物防',
              sp_attack: '特攻', sp_defense: '特防', speed: '速度',
            };
            return (
              <div key={s} className="stat-item">
                <span className="stat-label">{labels[s] ?? s}</span>
                <span className="stat-value">{bs[s] ?? '-'}</span>
              </div>
            );
          })}
        </div>
      )}

      {/* Moves */}
      {mon.moves.length > 0 && (
        <div className="moves-section">
          {mon.moves.map((move, i) => {
            const ppLow = move.pp_current != null && move.pp_max != null && move.pp_current <= Math.floor(move.pp_max * 0.25);
            const ppEmpty = move.pp_current != null && move.pp_current === 0;
            const typeColor = TYPE_COLORS[move.type] ?? '#888';
            return (
              <div
                key={i}
                className={'move-item' + (ppEmpty ? ' depleted' : '')}
                style={{ borderLeftColor: typeColor }}
                title={move.description || (move.name + ' (' + move.type + '/' + move.category + '/' + move.base_power + ')')}
              >
                <span className="move-name">{move.name}</span>
                <span className="move-cat">{catIcon(move.category)}</span>
                <span className="move-type-badge" style={{ background: typeColor }}>{move.type}</span>
                {move.base_power > 0 && <span className="move-power">{move.base_power}</span>}
                <span className={'move-pp' + (ppEmpty ? ' empty' : ppLow ? ' low' : '')}>
                  PP {move.pp_current ?? '?'}/{move.pp_max ?? '?'}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Main Page ──

const LOG_TYPE_COLORS: Record<string, string> = {
  turn: '#3b82f6',
  send_out: '#4ade80',
  use_move: '#fbbf24',
  hp_change: '#f87171',
  status_change: '#c084fc',
  switch: '#64748b',
  faint: '#ef4444',
  effectiveness: '#fb923c',
};

const LOG_TYPE_ICONS: Record<string, string> = {
  turn: '⏱',
  send_out: '🏃',
  use_move: '⚔️',
  hp_change: '💥',
  status_change: '🌀',
  switch: '🔄',
  faint: '💀',
  effectiveness: '🎯',
};

export default function HomePage() {
  const { sources, selectSource } = useVideoSources();
  const { state, restartSession, resetSession } = useRecognitionPolling(1000);
  const sourceSelectionInFlightRef = useRef<Promise<void> | null>(null);
  const [debugOpen, setDebugOpen] = useState(false);
  const [movesCache, setMovesCache] = useState<Record<string, MoveInfo>>({});

  const phase = state?.current_phase ?? 'unknown';

  // ── Read from BattleSession (new data model) with fallback ──
  const session: BattleSession | null = state?.battle_session ?? null;
  const useSession = !!(session && session.battle_id);
  const sessionPlayerActive: BattleMon | null = useSession ? session!.player_active : null;
  const sessionOpponentActive: BattleMon | null = useSession ? session!.opponent_active : null;
  const sessionPlayerTeam: BattleMon[] = useSession ? session!.player_team : [];
  const sessionOpponentTeam: BattleMon[] = useSession ? session!.opponent_team : [];
  const sessionLog: LogEntry[] = useSession ? session!.log : [];
  const sessionIsOver: boolean = useSession ? session!.is_over : false;

  // ── Legacy fallback persistence (when BattleSession unavailable) ──
  const persistentPlayerName = useRef<string | null>(null);
  const persistentOpponentName = useRef<string | null>(null);
  const persistentPlayerHp = useRef<number | null>(null);
  const persistentOpponentHp = useRef<number | null>(null);
  const persistentStatus = useRef<string | null>(null);
  const persistentMoveEntries = useRef<MoveEntry[]>([]);
  const persistentRoiPayloads = useRef<Record<string, RoiPayload>>({});

  const rois = state?.roi_payloads ?? {};

  // Legacy move extraction (unconditional hooks — always defined)
  const moveSlots = useMemo(() => {
    if (useSession) return [];
    const names: string[] = [];
    for (let i = 1; i <= 4; i++) {
      const slot = rois?.['move_slot_' + i];
      const name = slot?.pokemon_name ?? slot?.recognized_texts?.[0];
      if (name) names.push(name);
    }
    return names;
  }, [useSession, rois]);

  const moveEntries = useMemo(() => {
    if (useSession) return persistentMoveEntries.current;
    if (moveSlots.length === 0) return persistentMoveEntries.current;
    const uncached = moveSlots.filter(n => !movesCache[n]);
    if (uncached.length > 0) {
      searchMoves(uncached.join(',')).then((result) => {
        const updates = result.moves ?? {};
        setMovesCache(prev => ({ ...prev, ...updates }));
      }).catch(() => {});
    }
    const entries = moveSlots.map(name => {
      const info = movesCache[name];
      return {
        name,
        type: info?.type ?? 'Normal',
        category: info?.category ?? 'Physical' as const,
        basePower: info?.basePower ?? 0,
        pp: info?.pp ?? 15,
        currentPp: info?.pp ?? 15,
      };
    });
    persistentMoveEntries.current = entries;
    return entries;
  }, [useSession, moveSlots, movesCache]);

  // Legacy fallback refs update
  if (!useSession) {
    if (state?.battle_reset) {
      persistentPlayerName.current = null;
      persistentOpponentName.current = null;
      persistentPlayerHp.current = null;
      persistentOpponentHp.current = null;
      persistentMoveEntries.current = [];
      persistentStatus.current = null;
      persistentRoiPayloads.current = {};
    }
  }

  // Source selection handler
  const handleSelectSource = async (sourceId: string) => {
    if (sourceSelectionInFlightRef.current) return sourceSelectionInFlightRef.current;
    const pending = (async () => {
      await selectSource(sourceId);
      await restartSession();
    })().finally(() => {
      if (sourceSelectionInFlightRef.current === pending) sourceSelectionInFlightRef.current = null;
    });
    sourceSelectionInFlightRef.current = pending;
    return pending;
  };

  // Handle reset
  const handleResetData = useCallback(async () => {
    await resetSession();
  }, [resetSession]);

  // ── Render ──

  const showLog = phase === 'battle' || sessionLog.length > 0 || (state?.battle_state?.move_log?.length ?? 0) > 0;
  // For log display — prefer session logs, fall back to legacy move_log
  const displayLog: LogEntry[] = useSession
    ? sessionLog
    : (state?.battle_state?.move_log ?? []).map((entry) => ({
        type: typeof entry.type === 'string' ? entry.type : 'info',
        text: typeof entry.text === 'string' ? entry.text : '',
        timestamp: typeof entry.timestamp === 'string' ? entry.timestamp : '',
      }));

  return (
    <main className="app-layout">
      <TopBar
        sources={sources}
        selectedSourceId={sources.find(s => s.is_selected)?.id ?? sources[0]?.id ?? ''}
        debugOpen={debugOpen}
        onToggleDebug={() => setDebugOpen(d => !d)}
        onSelectSource={handleSelectSource}
        onResetData={handleResetData}
      />

      {debugOpen && (
        <div className="debug-section">
          <DebugInfoPanel state={state ?? null} />
        </div>
      )}

      <div className="main-content main-content-5col">
        {/* ── Column 1: Player Team ── */}
        <div className="col-team col-player-team">
          <h6 className="card-title" style={{ padding: '8px 8px 0 8px', margin: 0 }}>我方队伍</h6>
          <TeamSlots team={sessionPlayerTeam} />
        </div>

        {/* ── Column 2: Player Active Mon ── */}
        <div className="col-active col-player-active">
          {sessionIsOver ? (
            <div className="empty-state">
              <span>🏁</span>
              <p>对局结束</p>
            </div>
          ) : (
            <PokeCard mon={sessionPlayerActive} />
          )}
        </div>

        {/* ── Column 3: Battle Log ── */}
        <div className="col-center">
          {showLog ? (
            <div className="battle-log">
              <div className="battle-log-header">
                <div className={'phase-badge ' + (phase === 'battle' ? 'battle' : phase === 'final_result' ? 'end' : 'unknown')}>
                  {phase === 'battle' ? '战斗中' : phase === 'final_result' ? '对局结束' : '待命中'}
                </div>
                {displayLog.length > 0 && (
                  <button
                    className="copy-log-btn"
                    onClick={() => {
                      const text = displayLog.map(e => e.text).join('\n');
                      navigator.clipboard.writeText(text).catch(() => {});
                    }}
                  >
                    📋 复制全部
                  </button>
                )}
              </div>
              <div className="battle-log-list">
                {displayLog.length === 0 ? (
                  <p className="battle-log-empty">等待战斗记录…</p>
                ) : (
                  displayLog.slice().reverse().map((entry, i) => {
                    const color = LOG_TYPE_COLORS[entry.type] ?? '#64748b';
                    const icon = LOG_TYPE_ICONS[entry.type] ?? '•';
                    return (
                      <div key={i} className="battle-log-entry" style={{ borderLeftColor: color }}>
                        <span className="battle-log-icon">{icon}</span>
                        <span className="battle-log-text">{entry.text}</span>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          ) : phase === 'team_select' ? (
            <div className="empty-state">
              <span>📋</span>
              <p>选人阶段</p>
              <p className="empty-hint">等待阵容确认…</p>
            </div>
          ) : (
            <div className="empty-state">
              <span>📡</span>
              <p>等待视频源</p>
            </div>
          )}

          {/* Source info */}
          <div style={{ padding: '8px 12px', fontSize: '0.7rem', color: '#334155' }}>
            {state?.input_source ? '来源: ' + state.input_source : '无视频源'}
          </div>
        </div>

        {/* ── Column 4: Opponent Active Mon ── */}
        <div className="col-active col-opponent-active">
          {sessionIsOver ? (
            <div className="empty-state">
              <span>🏁</span>
              <p>对局结束</p>
            </div>
          ) : (
            <PokeCard mon={sessionOpponentActive} />
          )}
        </div>

        {/* ── Column 5: Opponent Team ── */}
        <div className="col-team col-opponent-team">
          <h6 className="card-title" style={{ padding: '8px 8px 0 8px', margin: 0 }}>对方队伍</h6>
          <TeamSlots team={sessionOpponentTeam} />
        </div>
      </div>
    </main>
  );
}
