import { fireEvent, render, screen } from '@testing-library/react';

import HomePage from '../app/page';

jest.mock('../lib/hooks', () => ({
  useVideoSources: () => ({
    sources: [
      {
        id: 'dev-battle',
        label: 'OBS Virtual Camera',
        backend: 'opencv',
        is_selected: true,
        device_index: 0,
        device_kind: 'virtual',
      },
    ],
    loading: false,
    refresh: jest.fn(),
  }),
  useRecognitionPolling: () => ({
    state: {
      current_phase: 'battle',
      layout_variant: 'battle_move_menu_open',
      phase_evidence: ['COMMAND 38', '招式说明', '雪妖女'],
      player_active_name: '烈咬陆鲨',
      opponent_active_name: '雪妖女',
      player: {
        name: '烈咬陆鲨',
        confidence: 0.98,
        source: 'ocr',
        debug_raw_text: '烈咬陆鲨',
        matched_by: 'exact',
      },
      opponent: {
        name: '雪妖女',
        confidence: 0.96,
        source: 'ocr',
        debug_raw_text: '雪妖女',
        matched_by: 'exact',
      },
      team_preview: null,
      timestamp: '2026-04-19T14:30:00Z',
      preview_image_data_url: 'data:image/jpeg;base64,battle-preview',
      roi_payloads: {
        player_status_panel: {
          role: 'battle-player-status-panel',
          source: 'roi-source-frame',
          pokemon_name: '烈咬陆鲨',
          hp_text: '183/183',
          hp_percentage: '100%',
          level: 'Lv.50',
          matched_by: 'ocr-status-panel',
          raw_texts: ['烈咬陆鲨', '183/183', '100%', 'Lv.50'],
          preview_image_data_url: 'data:image/jpeg;base64,player-status-preview',
        },
        opponent_status_panel: {
          role: 'battle-opponent-status-panel',
          source: 'roi-source-frame',
          pokemon_name: '雪妖女',
          hp_text: '100/100',
          hp_percentage: '100%',
          level: 'Lv.50',
          matched_by: 'ocr-status-panel',
          raw_texts: ['雪妖女', '100/100', '100%', 'Lv.50'],
          preview_image_data_url: 'data:image/jpeg;base64,opponent-status-preview',
        },
        move_list: {
          role: 'battle-move-list',
          source: 'roi-source-frame',
          recognized_texts: ['魔法闪耀', '岩崩', '逆鳞', '毒击'],
          recognized_count: 4,
          matched_by: 'ocr-text-list',
          preview_image_data_url: 'data:image/jpeg;base64,move-list-preview',
        },
      },
      frame_variants_debug: {
        phase_frame: {
          source: 'capture.frame_variants.phase_frame',
          width: 320,
          height: 180,
          preview_image_data_url: 'data:image/jpeg;base64,phase-preview',
        },
        roi_source_frame: {
          source: 'capture.frame_variants.roi_source_frame',
          width: 1920,
          height: 1080,
          preview_image_data_url: 'data:image/jpeg;base64,roi-preview',
        },
      },
    },
    loading: false,
    refresh: jest.fn(),
  }),
}));

describe('battle ROI debug panel', () => {
  it('renders structured battle panels for player, opponent, and move list', () => {
    render(<HomePage />);
    fireEvent.click(screen.getByRole('button', { name: '展开调试面板' }));

    expect(screen.getByText('布局模板：battle_move_menu_open')).toBeInTheDocument();
    expect(screen.getByText('battle 我方状态块：烈咬陆鲨 / 183/183 / 100% / Lv.50')).toBeInTheDocument();
    expect(screen.getByText('battle 对方状态块：雪妖女 / 100/100 / 100% / Lv.50')).toBeInTheDocument();
    expect(screen.getByText('battle 技能块：魔法闪耀 / 岩崩 / 逆鳞 / 毒击')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'player_status_panel ROI 预览' })).toHaveAttribute(
      'src',
      'data:image/jpeg;base64,player-status-preview',
    );
    expect(screen.getByRole('img', { name: 'opponent_status_panel ROI 预览' })).toHaveAttribute(
      'src',
      'data:image/jpeg;base64,opponent-status-preview',
    );
    expect(screen.getByRole('img', { name: 'move_list ROI 预览' })).toHaveAttribute(
      'src',
      'data:image/jpeg;base64,move-list-preview',
    );
  });
});
