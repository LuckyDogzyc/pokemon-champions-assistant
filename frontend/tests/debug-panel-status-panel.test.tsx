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
      matched_by: 'exact',
      debug_roi: { x: 0.08, y: 0.80, w: 0.22, h: 0.07, confidence: 'approx' },
    },
    opponent: {
      name: '皮卡丘',
      confidence: 0.87,
      source: 'ocr' as const,
      matched_by: 'fuzzy',
      debug_roi: { x: 0.70, y: 0.10, w: 0.22, h: 0.07, confidence: 'approx' },
    },
    timestamp: '2026-04-15T16:00:00Z',
    roi_payloads: {
      player_status_panel: {
        role: 'player_status_panel',
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
    },
    ...overrides,
  };
}

describe('DebugInfoPanel - status panels removed', () => {
  it('no longer renders battle ROI status card details', () => {
    render(<DebugInfoPanel state={makeState()} />);
    screen.getByText('展开调试面板').click();

    // Status panel cards should NOT appear
    expect(screen.queryByText(/宝可梦：烈咬陆鲨/)).not.toBeInTheDocument();
    expect(screen.queryByText(/HP：153\/204/)).not.toBeInTheDocument();
    expect(screen.queryByText(/HP 百分比：75%/)).not.toBeInTheDocument();
    expect(screen.queryByText(/等级：Lv.50/)).not.toBeInTheDocument();
    expect(screen.queryByText(/状态异常：中毒/)).not.toBeInTheDocument();

    // Opponent status panel cards should NOT appear
    expect(screen.queryByText(/宝可梦：皮卡丘/)).not.toBeInTheDocument();
  });

  it('still shows basic debug info', () => {
    render(<DebugInfoPanel state={makeState()} />);
    fireEvent.click(screen.getByText('展开调试面板'));

    expect(screen.getByText(/battle_default/)).toBeInTheDocument();
  });
});
