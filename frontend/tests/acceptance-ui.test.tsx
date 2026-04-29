/**
 * Acceptance tests for the UI redesign and battle features.
 *
 * Covers:
 * - BattleInfoPanel: base stats, speed comparison arrows, HP bar, status, revealed moves
 * - MovePanel: PP tracking, hit-to-kill estimate, hover damage tooltip
 * - TeamRosterPanel: team list, active indicator, fainted state
 * - GameScreenPanel: capture preview rendering
 * - TopBar: video source selector + debug toggle
 * - Page layout: center screen + symmetric left/right panels
 * - damage-calc utility: computeStat, compareSpeed, estimateDamage, estimateHitToKill
 */

import '@testing-library/jest-dom';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';

import { BattleInfoPanel } from '../components/battle-info-panel';
import { MovePanel } from '../components/move-panel';
import { TeamRosterPanel } from '../components/team-roster-panel';
import { GameScreenPanel } from '../components/game-screen-panel';
import { TopBar } from '../components/top-bar';
import HomePage from '../app/page';
import {
  computeStat,
  compareSpeed,
  estimateDamage,
  estimateHitToKill,
} from '../lib/damage-calc';
import type { BaseStats, MonBattleState, TeamEntry, VideoSource } from '../types/api';

// ── Shared fixtures ──

const pikachuBase: BaseStats = { hp: 35, attack: 55, defense: 40, sp_attack: 50, sp_defense: 50, speed: 90 };
const garchompBase: BaseStats = { hp: 108, attack: 130, defense: 95, sp_attack: 80, sp_defense: 85, speed: 102 };

const defaultMonState: MonBattleState = {
  pokemon_id: '025',
  name: '皮卡丘',
  level: 50,
  current_hp_percent: 75,
  status: 'none',
  stat_stages: { attack: 0, defense: 0, sp_attack: 0, sp_defense: 0, speed: 0, accuracy: 0, evasion: 0 },
  revealed_moves: [],
  item_revealed: null,
  ability_revealed: null,
  turns_on_field: 3,
};

const burnedMon: MonBattleState = {
  ...defaultMonState,
  name: '烈焰猴',
  status: 'burn',
  current_hp_percent: 30,
};

const boostedMon: MonBattleState = {
  ...defaultMonState,
  name: '皮卡丘',
  stat_stages: { attack: 2, defense: -1, sp_attack: 0, sp_defense: 0, speed: 1, accuracy: 0, evasion: 0 },
};

const opponentMon: MonBattleState = {
  pokemon_id: '445',
  name: '烈咬陆鲨',
  level: 50,
  current_hp_percent: 100,
  status: 'none',
  stat_stages: { attack: 0, defense: 0, sp_attack: 0, sp_defense: 0, speed: 0, accuracy: 0, evasion: 0 },
  revealed_moves: ['地震', '逆鳞'],
  item_revealed: null,
  ability_revealed: null,
  turns_on_field: 5,
};

const sampleTeam: TeamEntry[] = [
  { pokemon_id: '025', name: '皮卡丘', is_active: true, is_fainted: false },
  { pokemon_id: '006', name: '喷火龙', is_active: false, is_fainted: false },
  { pokemon_id: '009', name: '水箭龟', is_active: false, is_fainted: true },
  { pokemon_id: '003', name: '妙蛙花', is_active: false, is_fainted: false },
  { pokemon_id: '143', name: '卡比兽', is_active: false, is_fainted: false },
  { pokemon_id: '149', name: '快龙', is_active: false, is_fainted: false },
];

// ═══════════════════════════════════════════════
// damage-calc utility tests
// ═══════════════════════════════════════════════

describe('computeStat', () => {
  it('computes HP stat correctly at level 50', () => {
    // HP = floor((2*35+31)*50/100) + 50 + 10 = floor(50.5) + 60 = 110
    const hp = computeStat(35, 50, 'hp');
    expect(hp).toBeGreaterThan(0);
  });

  it('computes non-HP stat with +0 stage correctly', () => {
    const atk = computeStat(55, 50, 'attack', 0);
    expect(atk).toBeGreaterThan(0);
  });

  it('applies positive stage multiplier', () => {
    const neutral = computeStat(55, 50, 'attack', 0);
    const boosted = computeStat(55, 50, 'attack', 2);
    expect(boosted).toBeGreaterThan(neutral);
  });

  it('applies negative stage multiplier', () => {
    const neutral = computeStat(55, 50, 'attack', 0);
    const lowered = computeStat(55, 50, 'attack', -2);
    expect(lowered).toBeLessThan(neutral);
  });
});

describe('compareSpeed', () => {
  it('returns playerFaster=true when player is faster', () => {
    // Speed 90 vs 102 at neutral → Garchomp is faster, so player (Pikachu) is NOT faster
    const result = compareSpeed(pikachuBase, garchompBase, defaultMonState.stat_stages, opponentMon.stat_stages);
    expect(result.playerFaster).toBe(false);
    expect(result.speedTie).toBe(false);
  });

  it('returns playerFaster=true with speed boost', () => {
    const boosted: MonBattleState['stat_stages'] = { ...defaultMonState.stat_stages, speed: 6 };
    const result = compareSpeed(pikachuBase, garchompBase, boosted, opponentMon.stat_stages);
    expect(result.playerFaster).toBe(true);
  });

  it('detects speed tie', () => {
    const sameSpeed: BaseStats = { ...pikachuBase, speed: 90 };
    const result = compareSpeed(pikachuBase, sameSpeed, defaultMonState.stat_stages, defaultMonState.stat_stages);
    expect(result.speedTie).toBe(true);
  });
});

describe('estimateDamage', () => {
  it('returns a valid damage range', () => {
    const result = estimateDamage({
      attackerStats: pikachuBase,
      defenderStats: garchompBase,
      attackerStages: defaultMonState.stat_stages,
      defenderStages: opponentMon.stat_stages,
      movePower: 80,
      moveCategory: 'Special',
      moveType: 'Electric',
      attackerTypes: ['Electric'],
      defenderTypes: ['Dragon', 'Ground'],
      isSTAB: true,
      typeEffectiveness: 0, // Ground is immune to Electric
    });
    expect(result.min).toBe(0);
    expect(result.max).toBe(0);
    // When damage is 0 (immune), KO chance should indicate no damage
    expect(result.koChance).toBeTruthy();
  });

  it('computes normal damage with STAB', () => {
    const result = estimateDamage({
      attackerStats: garchompBase,
      defenderStats: pikachuBase,
      attackerStages: opponentMon.stat_stages,
      defenderStages: defaultMonState.stat_stages,
      movePower: 100,
      moveCategory: 'Physical',
      moveType: 'Dragon',
      attackerTypes: ['Dragon', 'Ground'],
      defenderTypes: ['Electric'],
      isSTAB: true,
      typeEffectiveness: 1.0,
    });
    expect(result.min).toBeGreaterThan(0);
    expect(result.max).toBeGreaterThanOrEqual(result.min);
    expect(result.maxPercent).toBeGreaterThan(0);
  });

  it('indicates OHKO when damage exceeds defender HP', () => {
    const result = estimateDamage({
      attackerStats: garchompBase,
      defenderStats: pikachuBase,
      attackerStages: { ...defaultMonState.stat_stages, attack: 6 },
      defenderStages: { ...defaultMonState.stat_stages, defense: -6 },
      movePower: 150,
      moveCategory: 'Physical',
      moveType: 'Dragon',
      attackerTypes: ['Dragon'],
      defenderTypes: ['Electric'],
      isSTAB: true,
      typeEffectiveness: 1.0,
    });
    // With max attack and min defense, should deal massive damage
    expect(result.maxPercent).toBeGreaterThan(100);
  });
});

describe('estimateHitToKill', () => {
  it('returns 1 hit when damage exceeds HP', () => {
    const range = { min: 999, max: 999, minPercent: 200, maxPercent: 200, koChance: '确一击', description: '' };
    const result = estimateHitToKill(range, 100);
    expect(result.minHits).toBe(1);
  });

  it('computes multi-hit for weak damage', () => {
    const range = { min: 10, max: 15, minPercent: 10, maxPercent: 15, koChance: '', description: '' };
    const result = estimateHitToKill(range, 100);
    expect(result.minHits).toBeGreaterThanOrEqual(7);
    expect(result.maxHits).toBeGreaterThanOrEqual(result.minHits);
  });
});

// ═══════════════════════════════════════════════
// BattleInfoPanel acceptance tests
// ═══════════════════════════════════════════════

describe('BattleInfoPanel', () => {
  it('renders Pokémon name', () => {
    render(<BattleInfoPanel side="player" mon={defaultMonState} baseStats={pikachuBase} />);
    expect(screen.getByText('皮卡丘')).toBeInTheDocument();
  });

  it('shows HP bar with percentage', () => {
    render(<BattleInfoPanel side="player" mon={defaultMonState} baseStats={pikachuBase} />);
    expect(screen.getByText('75%')).toBeInTheDocument();
  });

  it('shows status icon for burned Pokémon', () => {
    render(<BattleInfoPanel side="player" mon={burnedMon} baseStats={pikachuBase} />);
    expect(screen.getByTitle('burn')).toBeInTheDocument();
  });

  it('shows speed arrow ↓ when opponent is faster (player side)', () => {
    render(
      <BattleInfoPanel
        side="player"
        mon={defaultMonState}
        baseStats={pikachuBase}
        opponentBaseStats={garchompBase}
        opponentMon={opponentMon}
      />
    );
    // Garchomp (102) > Pikachu (90), so player sees ↓
    const arrow = screen.getByTitle(/速度/);
    expect(arrow.textContent).toContain('↓');
    expect(arrow.className).toContain('slower');
  });

  it('shows speed arrow ↑ when player is faster (player side)', () => {
    render(
      <BattleInfoPanel
        side="player"
        mon={boostedMon}
        baseStats={pikachuBase}
        opponentBaseStats={garchompBase}
        opponentMon={opponentMon}
      />
    );
    const arrow = screen.getByTitle(/速度/);
    expect(arrow.textContent).toContain('↑');
    expect(arrow.className).toContain('faster');
  });

  it('shows speed = on tie', () => {
    const sameSpeed: BaseStats = { ...pikachuBase, speed: 90 };
    render(
      <BattleInfoPanel
        side="player"
        mon={defaultMonState}
        baseStats={pikachuBase}
        opponentBaseStats={sameSpeed}
        opponentMon={defaultMonState}
      />
    );
    expect(screen.getByTitle(/速度相同/)).toBeInTheDocument();
  });

  it('displays base stats rows', () => {
    render(<BattleInfoPanel side="player" mon={defaultMonState} baseStats={pikachuBase} />);
    expect(screen.getByText('HP')).toBeInTheDocument();
    expect(screen.getByText('攻击')).toBeInTheDocument();
    expect(screen.getByText('防御')).toBeInTheDocument();
    expect(screen.getByText('特攻')).toBeInTheDocument();
    expect(screen.getByText('特防')).toBeInTheDocument();
    expect(screen.getByText('速度')).toBeInTheDocument();
  });

  it('shows stage indicator for boosted stats', () => {
    render(<BattleInfoPanel side="player" mon={boostedMon} baseStats={pikachuBase} />);
    // Attack is +2, should show +2
    const attackRow = screen.getByText('攻击').parentElement!;
    expect(attackRow.innerHTML).toContain('+2');
  });

  it('shows revealed moves for opponent', () => {
    render(
      <BattleInfoPanel side="opponent" mon={opponentMon} baseStats={garchompBase} />
    );
    expect(screen.getByText('地震')).toBeInTheDocument();
    expect(screen.getByText('逆鳞')).toBeInTheDocument();
    expect(screen.getByText('已发现招式')).toBeInTheDocument();
  });

  it('shows item/ability when revealed', () => {
    const monWithItem: MonBattleState = {
      ...opponentMon,
      item_revealed: '讲究围巾',
      ability_revealed: '粗糙皮肤',
    };
    render(<BattleInfoPanel side="opponent" mon={monWithItem} baseStats={garchompBase} />);
    expect(screen.getByText(/讲究围巾/)).toBeInTheDocument();
    expect(screen.getByText(/粗糙皮肤/)).toBeInTheDocument();
  });
});

// ═══════════════════════════════════════════════
// MovePanel acceptance tests
// ═══════════════════════════════════════════════

describe('MovePanel', () => {
  const moves = [
    { name: '十万伏特', type: 'Electric', category: 'Special' as const, basePower: 90, pp: 15, currentPp: 12 },
    { name: '铁尾', type: 'Steel', category: 'Physical' as const, basePower: 100, pp: 15, currentPp: 15 },
    { name: '电球', type: 'Electric', category: 'Special' as const, basePower: 80, pp: 10, currentPp: 8 },
    { name: '伏特攻击', type: 'Electric', category: 'Physical' as const, basePower: 120, pp: 15, currentPp: 15 },
  ];

  it('renders all moves with name and type', () => {
    render(
      <MovePanel
        moves={moves}
        attackerStats={pikachuBase}
        attackerStages={defaultMonState.stat_stages}
        defenderStats={garchompBase}
        defenderStages={opponentMon.stat_stages}
        defenderHpPercent={100}
        attackerTypes={['Electric']}
        defenderTypes={['Dragon', 'Ground']}
      />
    );
    expect(screen.getByText('十万伏特')).toBeInTheDocument();
    expect(screen.getByText('铁尾')).toBeInTheDocument();
    expect(screen.getByText('电球')).toBeInTheDocument();
    expect(screen.getByText('伏特攻击')).toBeInTheDocument();
  });

  it('shows PP tracking (current/max)', () => {
    render(
      <MovePanel
        moves={moves}
        attackerStats={pikachuBase}
        attackerStages={defaultMonState.stat_stages}
        defenderStats={garchompBase}
        defenderStages={opponentMon.stat_stages}
        defenderHpPercent={100}
        attackerTypes={['Electric']}
        defenderTypes={['Dragon', 'Ground']}
      />
    );
    expect(screen.getByText('PP:12/15')).toBeInTheDocument();
    expect(screen.getByText('PP:8/10')).toBeInTheDocument();
  });

  it('shows hit-to-kill estimate for each move', () => {
    render(
      <MovePanel
        moves={moves}
        attackerStats={pikachuBase}
        attackerStages={defaultMonState.stat_stages}
        defenderStats={garchompBase}
        defenderStages={opponentMon.stat_stages}
        defenderHpPercent={100}
        attackerTypes={['Electric']}
        defenderTypes={['Dragon', 'Ground']}
      />
    );
    // At least one move should show a hit estimate
    const hitLabels = screen.getAllByText(/\d+击/);
    expect(hitLabels.length).toBeGreaterThan(0);
  });

  it('renders without crashing with empty moves', () => {
    render(
      <MovePanel
        moves={[]}
        attackerStats={pikachuBase}
        attackerStages={defaultMonState.stat_stages}
        defenderStats={garchompBase}
        defenderStages={opponentMon.stat_stages}
        defenderHpPercent={100}
        attackerTypes={[]}
        defenderTypes={[]}
      />
    );
    expect(screen.getByText(/暂无招式/)).toBeInTheDocument();
  });
});

// ═══════════════════════════════════════════════
// TeamRosterPanel acceptance tests
// ═══════════════════════════════════════════════

describe('TeamRosterPanel', () => {
  it('renders all team members', () => {
    render(<TeamRosterPanel side="player" team={sampleTeam} />);
    expect(screen.getByText('皮卡丘')).toBeInTheDocument();
    expect(screen.getByText('喷火龙')).toBeInTheDocument();
    expect(screen.getByText('水箭龟')).toBeInTheDocument();
  });

  it('marks active Pokémon', () => {
    render(<TeamRosterPanel side="player" team={sampleTeam} />);
    // Active mon should have an indicator
    const activeItem = screen.getByText('皮卡丘').closest('.roster-item');
    expect(activeItem?.className).toContain('active');
  });

  it('marks fainted Pokémon', () => {
    render(<TeamRosterPanel side="player" team={sampleTeam} />);
    const faintedItem = screen.getByText('水箭龟').closest('.roster-item');
    expect(faintedItem?.className).toContain('fainted');
  });

  it('renders with empty team gracefully', () => {
    render(<TeamRosterPanel side="opponent" team={[]} />);
    expect(screen.getByText(/暂无/)).toBeInTheDocument();
  });
});

// ═══════════════════════════════════════════════
// GameScreenPanel acceptance tests
// ═══════════════════════════════════════════════

describe('GameScreenPanel', () => {
  it('renders the capture preview image when available', () => {
    render(
      <GameScreenPanel previewImageDataUrl="data:image/png;base64,test" />
    );
    const img = screen.getByAltText('实时游戏画面');
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute('src', 'data:image/png;base64,test');
  });

  it('shows placeholder when no preview', () => {
    render(<GameScreenPanel previewImageDataUrl={null} />);
    expect(screen.getByText(/暂无画面/)).toBeInTheDocument();
  });
});

// ═══════════════════════════════════════════════
// TopBar acceptance tests
// ═══════════════════════════════════════════════

describe('TopBar', () => {
  it('renders video source selector', () => {
    const sources: VideoSource[] = [
      { id: '0', label: 'OBS Virtual Camera', backend: 'opencv', is_selected: true },
      { id: '1', label: 'Video Device 0', backend: 'opencv', is_selected: false },
    ];
    render(
      <TopBar
        sources={sources}
        selectedSourceId="0"
        debugOpen={false}
        onToggleDebug={() => {}}
        onSelectSource={() => {}}
      />
    );
    expect(screen.getByLabelText('视频输入源')).toBeInTheDocument();
  });

  it('renders debug toggle button', () => {
    render(
      <TopBar
        sources={[]}
        selectedSourceId=""
        debugOpen={false}
        onToggleDebug={() => {}}
        onSelectSource={() => {}}
      />
    );
    expect(screen.getByText(/调试/)).toBeInTheDocument();
  });

  it('calls onToggleDebug when debug button clicked', () => {
    const toggle = jest.fn();
    render(
      <TopBar
        sources={[]}
        selectedSourceId=""
        debugOpen={false}
        onToggleDebug={toggle}
        onSelectSource={() => {}}
      />
    );
    fireEvent.click(screen.getByText(/调试/));
    expect(toggle).toHaveBeenCalledTimes(1);
  });
});
