'use client';

import type { TeamEntry } from '../types/api';

type Props = {
  side: 'player' | 'opponent';
  team: TeamEntry[];
  onSelectMon?: (pokemonId: string) => void;
};

export function TeamRosterPanel({ side, team, onSelectMon }: Props) {
  const isPlayer = side === 'player';
  const label = isPlayer ? '我方队伍' : '对方队伍';

  if (team.length === 0) {
    return (
      <div className={`team-roster-panel ${isPlayer ? 'player-side' : 'opponent-side'}`}>
        <h3 className="trp-title">{label}</h3>
        <p className="trp-empty">暂无队伍数据</p>
      </div>
    );
  }

  return (
    <div className={`team-roster-panel ${isPlayer ? 'player-side' : 'opponent-side'}`}>
      <h3 className="trp-title">{label}</h3>
      <div className="trp-list">
        {team.map((mon) => {
          const classes = [
            'roster-item',
            mon.is_active ? 'active' : '',
            mon.is_fainted ? 'fainted' : '',
          ].filter(Boolean).join(' ');

          return (
            <button
              key={mon.pokemon_id}
              className={classes}
              type="button"
              disabled={!isPlayer || mon.is_active}
              onClick={() => { if (mon.pokemon_id) onSelectMon?.(mon.pokemon_id); }}
              title={mon.is_fainted ? `${mon.name ?? ''} (已倒下)` : mon.is_active ? `${mon.name ?? ''} (场上)` : mon.name ?? ''}
            >
              <span className="roster-indicator">
                {mon.is_fainted ? '✕' : mon.is_active ? '●' : '○'}
              </span>
              <span className="roster-name">{mon.name}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
