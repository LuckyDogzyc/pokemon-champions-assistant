import { fireEvent, render, screen } from '@testing-library/react';

import { DebugInfoPanel } from '../components/debug-info-panel';

function makeState(overrides: Record<string, unknown> = {}) {
  return {
    current_phase: 'battle',
    layout_variant: 'battle_default',
    player: {
      name: '烈咬陆鲨',
      confidence: 0.92,
      source: 'ocr' as const,
      debug_raw_text: '烈咬陆鲨',
      matched_by: 'exact',
      debug_roi: { x: 0.08, y: 0.80, w: 0.22, h: 0.07, confidence: 'approx' },
    },
    opponent: {
      name: '皮卡丘',
      confidence: 0.87,
      source: 'ocr' as const,
      debug_raw_text: '皮卡丘',
      matched_by: 'fuzzy',
      debug_roi: { x: 0.70, y: 0.10, w: 0.22, h: 0.07, confidence: 'approx' },
    },
    timestamp: '2026-04-15T16:00:00Z',
    roi_payloads: {
      player_status_panel: {
        role: 'player_status_panel',
        source: 'roi-source-frame',
        pixel_box: { left: 16, top: 350, width: 220, height: 72 },
        crop_width: 220,
        crop_height: 72,
        pokemon_name: '烈咬陆鲨',
        hp_text: '153/204',
        hp_percentage: '75%',
        level: 'Lv.50',
        status_abnormality: '中毒',
        matched_by: 'ocr-status-panel',
        raw_texts: ['烈咬陆鲨', 'HP 153/204', '75%', 'Lv.50', '中毒'],
        raw_count: 5,
        preview_image_data_url: 'data:image/jpeg;base64,/9j/4AAQ==',
      },
      opponent_status_panel: {
        role: 'opponent_status_panel',
        source: 'roi-source-frame',
        pixel_box: { left: 438, top: 24, width: 180, height: 64 },
        crop_width: 180,
        crop_height: 64,
        pokemon_name: '皮卡丘',
        hp_text: '80/80',
        hp_percentage: '100%',
        level: 'Lv.50',
        matched_by: 'ocr-status-panel',
        raw_texts: ['皮卡丘', 'HP 80/80', '100%', 'Lv.50'],
        raw_count: 4,
        preview_image_data_url: 'data:image/jpeg;base64,/9j/4AAQ==',
      },
      move_list: {
        role: 'battle-move-list',
        source: 'roi-source-frame',
        pixel_box: { left: 468, top: 200, width: 148, height: 180 },
        crop_width: 148,
        crop_height: 180,
        recognized_texts: ['喷射火焰', '龙之舞', '地震', '守住'],
        recognized_count: 4,
        matched_by: 'ocr-text-list',
        preview_image_data_url: 'data:image/jpeg;base64,/9j/4AAQ==',
      },
    },
    ...overrides,
  };
}

describe('DebugInfoPanel - battle ROIs removed', () => {
  it('does not render the battle-roi-grid', () => {
    render(<DebugInfoPanel state={makeState()} />);

    // Open the debug panel
    fireEvent.click(screen.getByText('展开调试面板'));

    // The battle-roi-grid should not exist
    expect(screen.queryByTestId('battle-roi-grid')).not.toBeInTheDocument();

    // The individual ROI status texts should NOT appear (no longer rendered)
    // These were previously rendered by renderRoiCard for player_status_panel
    expect(screen.queryByText('player_status_panel（player_status_panel）')).not.toBeInTheDocument();
    expect(screen.queryByText('opponent_status_panel（opponent_status_panel）')).not.toBeInTheDocument();
    expect(screen.queryByText('move_list（battle-move-list）')).not.toBeInTheDocument();
    expect(screen.queryByText(/像素裁切框/)).not.toBeInTheDocument();
    expect(screen.queryByAltText('player_status_panel ROI 预览')).not.toBeInTheDocument();
    expect(screen.queryByAltText('opponent_status_panel ROI 预览')).not.toBeInTheDocument();
    expect(screen.queryByAltText('move_list ROI 预览')).not.toBeInTheDocument();
  });

  it('still renders other debug info', () => {
    render(<DebugInfoPanel state={makeState()} />);
    fireEvent.click(screen.getByText('展开调试面板'));

    // Basic debug info should still be present
    expect(screen.getByText(/battle_default/)).toBeInTheDocument();
    expect(screen.getByText(/我方原始文本/)).toBeInTheDocument();
    expect(screen.getByText(/对方原始文本/)).toBeInTheDocument();
    expect(screen.getByText(/抓帧方式/)).toBeInTheDocument();
  });
});
