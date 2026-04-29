'use client';

import type { BaseStats, MonBattleState, StatStages, StatusCondition } from '../types/api';
import { compareSpeed, computeStat } from '../lib/damage-calc';

type Props = {
  side: 'player' | 'opponent';
  mon: MonBattleState;
  baseStats?: BaseStats | null;
  opponentBaseStats?: BaseStats | null;
  opponentMon?: MonBattleState | null;
  level?: number;
};

const STATUS_ICONS: Record<StatusCondition, string> = {
  none: '',
  burn: '🔥',
  poison: '☠️',
  bad_poison: '☠️',
  paralysis: '⚡',
  sleep: '💤',
  freeze: '❄️',
  confusion: '🌀',
  flinch: '💥',
};

const STAT_LABELS: Record<keyof StatStages, string> = {
  attack: '攻击',
  defense: '防御',
  sp_attack: '特攻',
  sp_defense: '特防',
  speed: '速度',
  accuracy: '命中',
  evasion: '回避',
};

function hpBarColor(percent: number): string {
  if (percent > 50) return '#4caf50';
  if (percent > 20) return '#ff9800';
  return '#f44336';
}

function stageIndicator(stage: number): string {
  if (stage > 0) return `+${stage}`;
  if (stage < 0) return `${stage}`;
  return '';
}

function stageColor(stage: number): string {
  if (stage > 0) return '#4caf50';
  if (stage < 0) return '#f44336';
  return '#9e9e9e';
}

export function BattleInfoPanel({ side, mon, baseStats, opponentBaseStats, opponentMon, level = 50 }: Props) {
  const name = mon.name || '???';
  const hp = mon.current_hp_percent;
  const speedComparison = baseStats && opponentBaseStats && opponentMon
    ? compareSpeed(baseStats, opponentBaseStats, mon.stat_stages, opponentMon.stat_stages, level)
    : null;

  const isPlayer = side === 'player';

  return (
    <div className={`battle-info-panel ${isPlayer ? 'player-side' : 'opponent-side'}`}>
      {/* Header */}
      <div className="bip-header">
        <span className="bip-name">{name}</span>
        {mon.status !== 'none' && (
          <span className="bip-status-icon" title={mon.status}>{STATUS_ICONS[mon.status]}</span>
        )}
        {speedComparison && !speedComparison.speedTie && (
          <span
            className={`bip-speed-arrow ${speedComparison.playerFaster === isPlayer ? 'faster' : 'slower'}`}
            title={`速度: ${speedComparison.playerFaster === isPlayer ? speedComparison.playerSpeed : speedComparison.opponentSpeed}`}
          >
            {speedComparison.playerFaster === isPlayer ? '↑' : '↓'}
          </span>
        )}
        {speedComparison?.speedTie && (
          <span className="bip-speed-arrow tie" title={`速度相同: ${speedComparison.playerSpeed}`}>=</span>
        )}
      </div>

      {/* HP Bar */}
      <div className="bip-hp-row">
        <div className="bip-hp-bar-bg">
          <div
            className="bip-hp-bar-fill"
            style={{
              width: hp != null ? `${Math.max(0, Math.min(100, hp))}%` : '0%',
              backgroundColor: hp != null ? hpBarColor(hp) : '#9e9e9e',
            }}
          />
        </div>
        <span className="bip-hp-text">
          {hp != null ? `${Math.round(hp)}%` : '???'}
        </span>
      </div>

      {/* Base Stats */}
      {baseStats && (
        <div className="bip-base-stats">
          <div className="bip-stat-row">
            <span className="bip-stat-label">HP</span>
            <span className="bip-stat-value">{computeStat(baseStats.hp, level, 'hp')}</span>
          </div>
          <div className="bip-stat-row">
            <span className="bip-stat-label">攻击</span>
            <span className="bip-stat-value" style={{ color: stageColor(mon.stat_stages.attack) }}>
              {computeStat(baseStats.attack, level, 'attack', mon.stat_stages.attack)}
              {mon.stat_stages.attack !== 0 && <small>{stageIndicator(mon.stat_stages.attack)}</small>}
            </span>
          </div>
          <div className="bip-stat-row">
            <span className="bip-stat-label">防御</span>
            <span className="bip-stat-value" style={{ color: stageColor(mon.stat_stages.defense) }}>
              {computeStat(baseStats.defense, level, 'defense', mon.stat_stages.defense)}
              {mon.stat_stages.defense !== 0 && <small>{stageIndicator(mon.stat_stages.defense)}</small>}
            </span>
          </div>
          <div className="bip-stat-row">
            <span className="bip-stat-label">特攻</span>
            <span className="bip-stat-value" style={{ color: stageColor(mon.stat_stages.sp_attack) }}>
              {computeStat(baseStats.sp_attack, level, 'sp_attack', mon.stat_stages.sp_attack)}
              {mon.stat_stages.sp_attack !== 0 && <small>{stageIndicator(mon.stat_stages.sp_attack)}</small>}
            </span>
          </div>
          <div className="bip-stat-row">
            <span className="bip-stat-label">特防</span>
            <span className="bip-stat-value" style={{ color: stageColor(mon.stat_stages.sp_defense) }}>
              {computeStat(baseStats.sp_defense, level, 'sp_defense', mon.stat_stages.sp_defense)}
              {mon.stat_stages.sp_defense !== 0 && <small>{stageIndicator(mon.stat_stages.sp_defense)}</small>}
            </span>
          </div>
          <div className="bip-stat-row">
            <span className="bip-stat-label">速度</span>
            <span className="bip-stat-value" style={{ color: stageColor(mon.stat_stages.speed) }}>
              {computeStat(baseStats.speed, level, 'speed', mon.stat_stages.speed)}
              {mon.stat_stages.speed !== 0 && <small>{stageIndicator(mon.stat_stages.speed)}</small>}
            </span>
          </div>
        </div>
      )}

      {/* Revealed moves (for opponent) */}
      {side === 'opponent' && mon.revealed_moves.length > 0 && (
        <div className="bip-revealed-moves">
          <span className="bip-section-label">已发现招式</span>
          {mon.revealed_moves.map((move, i) => (
            <span key={i} className="bip-move-tag">{move}</span>
          ))}
        </div>
      )}

      {/* Item / Ability */}
      {(mon.item_revealed || mon.ability_revealed) && (
        <div className="bip-extras">
          {mon.item_revealed && <span className="bip-tag">道具: {mon.item_revealed}</span>}
          {mon.ability_revealed && <span className="bip-tag">特性: {mon.ability_revealed}</span>}
        </div>
      )}
    </div>
  );
}
