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

describe('DebugInfoPanel - ROI recognition results', () => {
  it('displays ROI OCR recognition results with crop previews and recognized text', () => {
    render(<DebugInfoPanel state={makeState()} />);
    fireEvent.click(screen.getByText('展开调试面板'));

    // ROI section heading
    expect(screen.getByText('ROI 分区 OCR 识别结果')).toBeInTheDocument();

    // Name cards should now appear inside the ROI section
    expect(screen.getByText('player_status_panel')).toBeInTheDocument();
    expect(screen.getByText('opponent_status_panel')).toBeInTheDocument();

    // Status panel details shown (may appear multiple times: once in plain text, once in raw JSON)
    expect(screen.getAllByText(/烈咬陆鲨/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText((content: string) => content.includes('153/204')).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText((content: string) => content.includes('75%')).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/中毒/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('皮卡丘').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText((content: string) => content.includes('80/80')).length).toBeGreaterThanOrEqual(1);
  });

  it('still shows basic debug info', () => {
    render(<DebugInfoPanel state={makeState()} />);
    fireEvent.click(screen.getByText('展开调试面板'));

    expect(screen.getByText(/battle_default/)).toBeInTheDocument();
  });
});
