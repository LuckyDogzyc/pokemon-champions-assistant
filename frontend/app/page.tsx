'use client';

import { useRef, useState, useMemo } from 'react';

import type { BattleState, MoveInfo, RecognitionState, RoiPayload } from '../types/api';
import { DebugInfoPanel } from '../components/debug-info-panel';
import { TopBar } from '../components/top-bar';
import { useRecognitionPolling, useVideoSources } from '../lib/hooks';
import { searchMoves } from '../lib/api';

// ── Helpers ──

function findRoiPayload(roiPayloads: Record<string, RoiPayload> | undefined, key: string): RoiPayload | null {
  return roiPayloads?.[key] ?? null;
}

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

function TeamSlots({ rois, side }: { rois: Record<string, RoiPayload> | undefined; side: string }) {
  const slots = [];
  for (let i = 1; i <= 6; i++) {
    const key = side + '_mon_' + i;
    const slot = rois?.[key];
    const name = slot?.pokemon_name ?? rois?.[key]?.recognized_texts?.[0];
    slots.push(
      <div key={key} className={'team-slot' + (slot?.is_selected ? ' selected' : '')}>
        <span className="team-slot-name">{name ?? '空位 ' + i}</span>
        {slot?.item && <span className="team-slot-item">{String(slot.item)}</span>}
        {slot?.gender && <span className="team-slot-gender">{String(slot.gender)}</span>}
      </div>,
    );
  }
  return <div className="team-grid">{slots}</div>;
}

function PokeCard({
  name,
  item,
  gender,
  hpText,
  hpPercent,
  level,
  status,
  moves,
  speedLabel,
}: {
  name: string | null;
  item?: string | null;
  gender?: string | null;
  hpText?: string | null;
  hpPercent?: number | null;
  level?: number;
  status?: string | null;
  moves?: MoveEntry[];
  speedLabel?: string | null;
}) {
  const hp = hpPercent ?? 100;
  const hpColor = hp > 50 ? '#4ade80' : hp > 20 ? '#fb923c' : '#f87171';

  return (
    <div className="poke-card">
      <div className="poke-header">
        <span className="poke-name">{name ?? '???'}</span>
        {item && <span className="poke-item">{String(item)}</span>}
        {gender && <span className="poke-gender">{String(gender)}</span>}
        {level && <span className="poke-level">Lv.{level}</span>}
      </div>

      {status && status !== 'none' && (
        <div className="status-badge">{status}</div>
      )}

      <div className="hp-row">
        <div className="hp-bar-bg">
          <div className="hp-bar-fill" style={{ width: Math.max(0, Math.min(100, hp)) + '%', backgroundColor: hpColor }} />
        </div>
        <span className="hp-text">{hpText ?? Math.round(hp) + '%'}</span>
      </div>

      {speedLabel && <div className={'speed-row ' + speedLabel}>{speedLabel === 'faster' ? '↑ 速度优势' : speedLabel === 'slower' ? '↓ 速度劣势' : '= 速度相同'}</div>}

      {moves && moves.length > 0 && (
        <div className="moves-section">
          <h4 className="moves-title">招式</h4>
          {moves.map((move, i) => {
            const ppLow = move.currentPp <= Math.floor(move.pp * 0.25);
            const ppEmpty = move.currentPp === 0;
            const typeColor = TYPE_COLORS[move.type] ?? '#888';
            return (
              <div key={i} className={'move-item' + (ppEmpty ? ' depleted' : '')} style={{ borderLeftColor: typeColor }}>
                <span className="move-name">{move.name}</span>
                <span className="move-cat">{catIcon(move.category)}</span>
                <span className="move-type-badge" style={{ background: typeColor }}>{move.type}</span>
                {move.basePower > 0 && <span className="move-power">{move.basePower}</span>}
                <span className={'move-pp' + (ppEmpty ? ' empty' : ppLow ? ' low' : '')}>
                  PP {move.currentPp}/{move.pp}
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
  const { state, restartSession } = useRecognitionPolling(2000);
  const sourceSelectionInFlightRef = useRef<Promise<void> | null>(null);
  const [debugOpen, setDebugOpen] = useState(false);
  const [movesCache, setMovesCache] = useState<Record<string, MoveInfo>>({});

  const phase = state?.current_phase ?? 'unknown';
  const rois = state?.roi_payloads ?? {};
  const playerSide = state?.player;
  const opponentSide = state?.opponent;

  // Extract moves from ROI payloads (battle phase)
  const moveSlots = useMemo(() => {
    const names: string[] = [];
    for (let i = 1; i <= 4; i++) {
      const slot = rois?.['move_slot_' + i];
      const name = slot?.pokemon_name ?? slot?.recognized_texts?.[0];
      if (name) names.push(name);
    }
    return names;
  }, [rois]);

  // Lookup move info
  const moveEntries = useMemo(() => {
    if (moveSlots.length === 0) return [];
    const uncached = moveSlots.filter(n => !movesCache[n]);
    if (uncached.length > 0) {
      searchMoves(uncached.join(',')).then((result) => {
        const updates = result.moves ?? {};
        setMovesCache(prev => ({ ...prev, ...updates }));
      }).catch(() => {});
    }
    return moveSlots.map(name => {
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
  }, [moveSlots, movesCache]);

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

  // Get player/opponent info from ROI
  const playerStatusRoi = findRoiPayload(rois, 'player_status_panel');
  const opponentStatusRoi = findRoiPayload(rois, 'opponent_status_panel');
  const playerName = playerSide?.name ?? playerStatusRoi?.pokemon_name ?? null;
  const opponentName = opponentSide?.name ?? opponentStatusRoi?.pokemon_name ?? null;

  return (
    <main className="app-layout">
      <TopBar
        sources={sources}
        selectedSourceId={sources.find(s => s.is_selected)?.id ?? sources[0]?.id ?? ''}
        debugOpen={debugOpen}
        onToggleDebug={() => setDebugOpen(d => !d)}
        onSelectSource={handleSelectSource}
      />

      {debugOpen && (
        <div className="debug-section">
          <DebugInfoPanel state={state ?? null} />
        </div>
      )}

      <div className="main-content">
        {/* ── Left: Player side ── */}
        <div className="col-player">
          {phase === 'team_select' ? (
            <>
              <h6 className="card-title" style={{ padding: '8px 8px 0 8px', margin: 0 }}>我方队伍</h6>
              <TeamSlots rois={rois} side="player" />
            </>
          ) : phase === 'battle' ? (
            <PokeCard
              name={playerName}
              item={playerStatusRoi?.raw_texts?.find(t => t.includes('果') || t.includes('带')) ?? null}
              hpText={playerStatusRoi?.hp_text ?? (state?.player_hp_current != null && state?.player_hp_max != null ? state.player_hp_current + '/' + state.player_hp_max : null)}
              hpPercent={state?.player_hp_current != null && state?.player_hp_max != null ? (state.player_hp_current / state.player_hp_max) * 100 : null}
              status={playerStatusRoi?.status_abnormality ?? null}
              moves={moveEntries}
            />
          ) : (
            <div className="empty-state">
              <span>🎮</span>
              <p>{phase === 'unknown' ? '等待画面信号' : phase}</p>
              <p className="empty-hint">{state?.input_source ? '来源: ' + state.input_source : '请选择视频输入源'}</p>
            </div>
          )}
        </div>

        {/* ── Center: Battle Log ── */}
        <div className="col-center">
          {phase === 'battle' ? (
            <div className="battle-log">
              <div className={'phase-badge ' + phase}>战斗中</div>
              <div className="battle-log-list">
                {(state?.battle_state?.move_log ?? []).length === 0 ? (
                  <p className="battle-log-empty">等待战斗记录…</p>
                ) : (
                  (state?.battle_state?.move_log ?? []).slice().reverse().map((entry, i) => {
                    const type = (entry.type as string) || '';
                    const color = LOG_TYPE_COLORS[type] ?? '#64748b';
                    const icon = LOG_TYPE_ICONS[type] ?? '•';
                    return (
                      <div key={i} className="battle-log-entry" style={{ borderLeftColor: color }}>
                        <span className="battle-log-icon">{icon}</span>
                        <span className="battle-log-text">{entry.text as string}</span>
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

        {/* ── Right: Opponent side ── */}
        <div className="col-opponent">
          {phase === 'team_select' ? (
            <>
              <h6 className="card-title" style={{ padding: '8px 8px 0 8px', margin: 0 }}>对方队伍</h6>
              <TeamSlots rois={rois} side="opponent" />
            </>
          ) : phase === 'battle' ? (
            <PokeCard
              name={opponentName}
              hpText={opponentStatusRoi?.hp_percentage ? String(opponentStatusRoi.hp_percentage) : null}
              hpPercent={opponentStatusRoi?.hp_percentage ? parseFloat(opponentStatusRoi.hp_percentage) : null}
              moves={[]}
            />
          ) : (
            <div className="empty-state">
              <span>🎮</span>
              <p>等待画面</p>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
