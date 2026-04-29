/**
 * Test: status panel ROI structured display in debug panel.
 * Separate file because it needs different jest.mock data than the existing debug-panel test.
 */
import { fireEvent, render, screen } from '@testing-library/react';

import HomePage from '../app/page';

jest.mock('../lib/hooks', () => ({
  useVideoSources: () => ({
    sources: [
      {
        id: 'dev-0',
        label: 'OBS Virtual Camera',
        backend: 'opencv',
        is_selected: true,
        device_index: 0,
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
      layout_variant: 'single_battle_default',
      phase_evidence: [],
      player_active_name: '烈咬陆鲨',
      opponent_active_name: '火神蛾',
      player: {
        name: '烈咬陆鲨',
        confidence: 0.99,
        source: 'ocr',
        debug_raw_text: '烈咬陆鲨',
        matched_by: 'ocr',
      },
      opponent: {
        name: '火神蛾',
        confidence: 0.97,
        source: 'ocr',
        debug_raw_text: '火神蛾',
        matched_by: 'ocr',
      },
      team_preview: { player_team: [], opponent_team: [], selected_count: 0 },
      input_source: 'dev-0',
      timestamp: '2026-04-19T00:00:00Z',
      preview_image_data_url: 'data:image/jpeg;base64,debug-preview',
      roi_payloads: {
        player_status_panel: {
          role: 'player_status_panel',
          pokemon_name: '烈咬陆鲨',
          hp_text: '120/150',
          hp_percentage: '80%',
          level: 'Lv.50',
          status_abnormality: '中毒',
          raw_texts: ['烈咬陆鲨', 'HP 120/150 80%', 'Lv.50', '中毒'],
          raw_count: 4,
          matched_by: 'ocr-structured',
          recognized_texts: [],
          recognized_count: 0,
        },
        opponent_status_panel: {
          role: 'opponent_status_panel',
          pokemon_name: '火神蛾',
          hp_text: '90/130',
          hp_percentage: '69%',
          level: 'Lv.48',
          status_abnormality: null,
          raw_texts: ['火神蛾', 'HP 90/130 69%', 'Lv.48'],
          raw_count: 3,
          matched_by: 'ocr-structured',
          recognized_texts: [],
          recognized_count: 0,
        },
      },
    },
    loading: false,
    refresh: jest.fn(),
  }),
}));

jest.mock('../lib/api', () => ({
  searchMoves: jest.fn(() => Promise.resolve({ moves: {} })),
}));

describe('status panel ROI in debug panel', () => {
  it('renders player status panel with structured name/HP/level/abnormality', () => {
    render(<HomePage />);
    // New UI: click "调试" to show debug section, then "展开调试面板" inside
    fireEvent.click(screen.getByText('调试'));
    fireEvent.click(screen.getByRole('button', { name: '展开调试面板' }));

    // player status panel structured fields
    expect(screen.getByText('player_status_panel（player_status_panel）')).toBeInTheDocument();
    expect(screen.getByText('🎴 宝可梦：烈咬陆鲨')).toBeInTheDocument();
    expect(screen.getByText('❤️ HP：120/150')).toBeInTheDocument();
    expect(screen.getByText('📊 HP 百分比：80%')).toBeInTheDocument();
    expect(screen.getByText('⭐ 等级：Lv.50')).toBeInTheDocument();
    expect(screen.getByText('⚠️ 状态异常：中毒')).toBeInTheDocument();
    // both panels have matched_by, so expect 2 occurrences
    expect(screen.getAllByText('识别方式：ocr-structured')).toHaveLength(2);
  });

  it('renders opponent status panel without status abnormality when null', () => {
    render(<HomePage />);
    fireEvent.click(screen.getByText('调试'));
    fireEvent.click(screen.getByRole('button', { name: '展开调试面板' }));

    // opponent status panel
    expect(screen.getByText('opponent_status_panel（opponent_status_panel）')).toBeInTheDocument();
    expect(screen.getByText('🎴 宝可梦：火神蛾')).toBeInTheDocument();
    expect(screen.getByText('❤️ HP：90/130')).toBeInTheDocument();
    expect(screen.getByText('📊 HP 百分比：69%')).toBeInTheDocument();
    expect(screen.getByText('⭐ 等级：Lv.48')).toBeInTheDocument();
    // opponent has no status abnormality, but player does — so exactly one ⚠️ element
    expect(screen.getAllByText(/⚠️ 状态异常/)).toHaveLength(1);
  });
});
