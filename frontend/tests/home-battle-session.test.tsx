import { render, screen } from '@testing-library/react';

import HomePage from '../app/page';

jest.mock('../lib/hooks', () => ({
  useVideoSources: () => ({
    sources: [
      {
        id: 'device-0',
        label: 'OBS Virtual Camera',
        backend: 'opencv',
        is_selected: true,
        device_kind: 'virtual',
      },
    ],
    loading: false,
    refresh: jest.fn(),
    selectSource: jest.fn(),
  }),
  useRecognitionPolling: () => ({
    state: {
      current_phase: 'battle',
      player_active_name: '错误的旧我方',
      opponent_active_name: '错误的旧对方',
      player: { name: '错误的旧我方', confidence: 0.1, source: 'mock' },
      opponent: { name: '错误的旧对方', confidence: 0.1, source: 'mock' },
      input_source: 'device-0',
      timestamp: '2026-05-03T12:00:00Z',
      battle_session: {
        battle_id: 'battle-session-fixture',
        turn: 3,
        is_over: false,
        reset_timestamp: null,
        player_team: [
          {
            name: '烈咬陆鲨',
            species: '烈咬陆鲨',
            pokemon_id: 'garchomp',
            types: ['Dragon', 'Ground'],
            base_stats: { hp: 108, attack: 130, defense: 95, sp_attack: 80, sp_defense: 85, speed: 102 },
            item: '凸凸头盔',
            gender: 'male',
            level: 50,
            current_hp: null,
            max_hp: null,
            current_hp_percent: null,
            status: [],
            stat_stages: {},
            buffs: [],
            debuffs: [],
            moves: [],
            revealed_move_names: [],
            is_fainted: false,
            turns_on_field: 0,
          },
        ],
        opponent_team: [
          {
            name: '赛富豪',
            species: '赛富豪',
            pokemon_id: 'gholdengo',
            types: ['Steel', 'Ghost'],
            base_stats: { hp: 87, attack: 60, defense: 95, sp_attack: 133, sp_defense: 91, speed: 84 },
            item: null,
            gender: null,
            level: 50,
            current_hp: null,
            max_hp: null,
            current_hp_percent: null,
            status: [],
            stat_stages: {},
            buffs: [],
            debuffs: [],
            moves: [],
            revealed_move_names: [],
            is_fainted: false,
            turns_on_field: 0,
          },
        ],
        player_active: {
          name: '烈咬陆鲨',
          species: '烈咬陆鲨',
          pokemon_id: 'garchomp',
          types: ['Dragon', 'Ground'],
          base_stats: { hp: 108, attack: 130, defense: 95, sp_attack: 80, sp_defense: 85, speed: 102 },
          item: '凸凸头盔',
          gender: 'male',
          level: 50,
          current_hp: 153,
          max_hp: 204,
          current_hp_percent: 75,
          status: ['poison'],
          stat_stages: {},
          buffs: [],
          debuffs: [],
          moves: [
            {
              name: 'Earthquake',
              type: 'Ground',
              category: 'Physical',
              base_power: 100,
              pp_current: 8,
              pp_max: 10,
              description: 'Hits adjacent Pokémon.',
            },
          ],
          revealed_move_names: ['Earthquake'],
          is_fainted: false,
          turns_on_field: 2,
        },
        opponent_active: {
          name: '赛富豪',
          species: '赛富豪',
          pokemon_id: 'gholdengo',
          types: ['Steel', 'Ghost'],
          base_stats: { hp: 87, attack: 60, defense: 95, sp_attack: 133, sp_defense: 91, speed: 84 },
          item: null,
          gender: null,
          level: 50,
          current_hp: null,
          max_hp: null,
          current_hp_percent: 62.5,
          status: [],
          stat_stages: {},
          buffs: [],
          debuffs: [],
          moves: [],
          revealed_move_names: [],
          is_fainted: false,
          turns_on_field: 2,
        },
        log: [
          { type: 'send_out', text: '我方 派出了 烈咬陆鲨', timestamp: '1' },
          { type: 'use_move', text: '烈咬陆鲨 使用了 Earthquake', timestamp: '2' },
        ],
      },
    },
    loading: false,
    refresh: jest.fn(),
    restartSession: jest.fn(),
    resetSession: jest.fn(),
  }),
}));

jest.mock('../lib/api', () => ({
  searchMoves: jest.fn(() => Promise.resolve({ moves: {} })),
}));

describe('Home page BattleSession contract', () => {
  it('renders team, active mons, moves, HP and log from battle_session instead of legacy recognition fields', () => {
    render(<HomePage />);

    expect(screen.getAllByText('烈咬陆鲨').length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('赛富豪').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('153/204 75%')).toBeInTheDocument();
    expect(screen.getByText('63%')).toBeInTheDocument();
    expect(screen.getByText('poison')).toBeInTheDocument();
    expect(screen.getByText('Earthquake')).toBeInTheDocument();
    expect(screen.getByText('PP 8/10')).toBeInTheDocument();
    expect(screen.getByText('烈咬陆鲨 使用了 Earthquake')).toBeInTheDocument();

    expect(screen.queryByText('错误的旧我方')).not.toBeInTheDocument();
    expect(screen.queryByText('错误的旧对方')).not.toBeInTheDocument();
  });
});
