'use client';

import type { BaseStats, StatStages } from '../types/api';
import { estimateDamage, estimateHitToKill } from '../lib/damage-calc';

export interface MoveEntry {
  name: string;
  type: string;
  category: 'Physical' | 'Special' | 'Status';
  basePower: number;
  pp: number;
  currentPp: number;
}

type Props = {
  moves: MoveEntry[];
  attackerStats: BaseStats;
  attackerStages: StatStages;
  defenderStats: BaseStats;
  defenderStages: StatStages;
  defenderHpPercent: number;
  attackerTypes: string[];
  defenderTypes: string[];
};

const TYPE_COLORS: Record<string, string> = {
  Normal: '#A8A878', Fire: '#F08030', Water: '#6890F0', Electric: '#F8D030',
  Grass: '#78C850', Ice: '#98D8D8', Fighting: '#C03028', Poison: '#A040A0',
  Ground: '#E0C068', Flying: '#A890F0', Psychic: '#F85888', Bug: '#A8B820',
  Rock: '#B8A038', Ghost: '#705898', Dragon: '#7038F8', Dark: '#705848',
  Steel: '#B8B8D0', Fairy: '#EE99AC',
};

function categoryIcon(cat: MoveEntry['category']): string {
  if (cat === 'Physical') return '⚔️';
  if (cat === 'Special') return '🔮';
  return '✦';
}

function isSTAB(moveType: string, attackerTypes: string[]): boolean {
  return attackerTypes.some(t => t.toLowerCase() === moveType.toLowerCase());
}

export function MovePanel({
  moves, attackerStats, attackerStages,
  defenderStats, defenderStages, defenderHpPercent,
  attackerTypes, defenderTypes,
}: Props) {
  if (moves.length === 0) {
    return (
      <div className="move-panel">
        <h3 className="mp-title">招式</h3>
        <p className="mp-empty">暂无招式数据</p>
      </div>
    );
  }

  return (
    <div className="move-panel">
      <h3 className="mp-title">招式</h3>
      <div className="mp-list">
        {moves.map((move) => {
          const damage = move.basePower > 0
            ? estimateDamage({
                attackerStats,
                defenderStats,
                attackerStages,
                defenderStages,
                movePower: move.basePower,
                moveCategory: move.category === 'Status' ? 'Special' : move.category,
                moveType: move.type,
                attackerTypes,
                defenderTypes,
                isSTAB: isSTAB(move.type, attackerTypes),
                defenderHpPercent,
              })
            : null;

          const htk = damage ? estimateHitToKill(damage, defenderHpPercent) : null;
          const ppLow = move.currentPp <= Math.floor(move.pp * 0.25);
          const ppDepleted = move.currentPp === 0;
          const typeColor = TYPE_COLORS[move.type] ?? '#888';

          return (
            <div
              key={move.name}
              className={`mp-item ${ppDepleted ? 'depleted' : ''}`}
              title={damage ? `${damage.description}\nKO: ${damage.koChance}` : undefined}
            >
              {/* Type color accent */}
              <div className="mp-item-accent" style={{ backgroundColor: typeColor }} />

              <div className="mp-item-body">
                <div className="mp-item-header">
                  <span className="mp-move-name">{move.name}</span>
                  <span className="mp-category">{categoryIcon(move.category)}</span>
                  <span className="mp-type-badge" style={{ backgroundColor: typeColor }}>
                    {move.type}
                  </span>
                </div>

                <div className="mp-item-stats">
                  <span className={`mp-pp ${ppLow ? 'low' : ''} ${ppDepleted ? 'depleted' : ''}`}>
                    {`PP:${move.currentPp}/${move.pp}`}
                  </span>
                  {move.basePower > 0 && (
                    <span className="mp-power">威力: {move.basePower}</span>
                  )}
                  {isSTAB(move.type, attackerTypes) && (
                    <span className="mp-stab">STAB</span>
                  )}
                </div>

                {damage && htk && (
                  <div className="mp-item-damage">
                    <span className="mp-damage-range">
                      {`${damage.minPercent}%–${damage.maxPercent}%`}
                    </span>
                    <span className="mp-ko-chance">{damage.koChance}</span>
                  </div>
                )}
              </div>

              {/* Hover tooltip for damage vs back-row (future: show vs each enemy team member) */}
              {damage && (
                <div className="mp-tooltip">
                  <p>伤害: {damage.min}–{damage.max}</p>
                  <p>占比: {damage.minPercent}%–{damage.maxPercent}%</p>
                  <p>{damage.koChance}</p>
                  {htk && <p>预计 {htk.minHits}–{htk.maxHits} 击</p>}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
