import { fireEvent, render, screen } from '@testing-library/react';

import HomePage from '../app/page';

jest.mock('../lib/hooks', () => ({
  useVideoSources: () => ({
    sources: [
      {
        id: 'device-0',
        label: 'USB Capture Card',
        backend: 'opencv',
        is_selected: true,
        device_index: 0,
      },
    ],
    loading: false,
    refresh: jest.fn(),
    selectSource: jest.fn(),
  }),
  useRecognitionPolling: () => ({
    state: {
      current_phase: 'team_select',
      layout_variant: 'team_select_default',
      phase_evidence: ['请选择出3只要上场战斗的宝可梦。', '选择完毕'],
      player_active_name: null,
      opponent_active_name: null,
      player: {
        name: null,
        confidence: 0,
        source: 'mock',
        debug_raw_text: '河马兽',
        debug_roi: { x: 0.03, y: 0.15, w: 0.32, h: 0.62, confidence: 'approx' },
        matched_by: 'exact',
      },
      opponent: {
        name: null,
        confidence: 0,
        source: 'mock',
        debug_raw_text: '火神蛾',
        debug_roi: { x: 0.69, y: 0.15, w: 0.27, h: 0.62, confidence: 'approx' },
        matched_by: 'exact',
      },
      team_preview: {
        player_team: ['河马兽', '烈咬陆鲨', '幽尾玄鱼'],
        opponent_team: ['火神蛾', '西狮海壬', '烈咬陆鲨'],
        selected_count: 0,
        instruction_text: '请选择出3只要上场战斗的宝可梦。',
      },
      input_source: 'device-0',
      timestamp: '2026-04-15T16:30:00Z',
      preview_image_data_url: 'data:image/jpeg;base64,debug-preview',
      recognition_error: 'ocr_runtime_error',
      recognition_error_detail: 'OneDnnContext does not have the input Filter',
      roi_payloads: {
        instruction_banner: {
          role: 'phase-detection',
          source: 'phase-frame',
          recognized_texts: ['请选择出3只要上场战斗的宝可梦。', '选择完毕', '0/3'],
          recognized_count: 3,
          matched_by: 'ocr-text-list',
          preview_image_data_url: 'data:image/jpeg;base64,instruction-preview',
        },
        player_team_list: {
          role: 'player_team_list',
          source: 'roi-source-frame',
          recognized_texts: ['喷射鸭', '象牙猪', '快龙'],
          recognized_count: 3,
          matched_by: 'ocr-text-list',
          preview_image_data_url: 'data:image/jpeg;base64,player-team-preview',
        },
        opponent_team_list: {
          role: 'opponent_team_list',
          source: 'roi-source-frame',
          recognized_texts: ['kubera', '火神蛾', '西狮海壬'],
          recognized_count: 3,
          matched_by: 'ocr-text-list',
          preview_image_data_url: 'data:image/jpeg;base64,opponent-team-preview',
        },
        move_list: {
          role: 'battle-move-list',
          recognized_texts: ['日光束', '魔法闪耀', '光合作用', '气象球'],
          recognized_count: 4,
          matched_by: 'ocr-text-list',
          preview_image_data_url: 'data:image/jpeg;base64,move-list-preview',
        },
      },
      capture_error: 'ffmpeg_read_failed',
      capture_error_detail: 'device returned no frames',
      capture_method: 'ffmpeg-dshow',
      capture_backend: 'dshow',
      frame_variants_debug: {
        phase_frame: {
          source: 'base-frame-fallback',
          width: 640,
          height: 360,
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

jest.mock('../lib/api', () => ({
  searchMoves: jest.fn(() => Promise.resolve({ moves: {} })),
}));

describe('dashboard debug panel', () => {
  it('supports toggling detailed debug info and renders structured evidence, matcher, and team preview details', () => {
    render(<HomePage />);

    // Step 1: Click "调试" in TopBar to show the debug section
    expect(screen.getByText('调试')).toBeInTheDocument();
    fireEvent.click(screen.getByText('调试'));

    // Step 2: The DebugInfoPanel is visible but collapsed; click "展开调试面板" to expand
    expect(screen.getByRole('button', { name: '展开调试面板' })).toBeInTheDocument();
    expect(screen.queryByText('布局模板：team_select_default')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '展开调试面板' }));

    // Now the full debug info is visible
    expect(screen.getByText('调试信息')).toBeInTheDocument();
    expect(screen.getByText('布局模板：team_select_default')).toBeInTheDocument();
    expect(screen.getByText('阶段证据')).toBeInTheDocument();
    expect(screen.getByText('请选择出3只要上场战斗的宝可梦。')).toBeInTheDocument();
    expect(screen.getByText('选择完毕')).toBeInTheDocument();
    expect(screen.getByText('我方原始文本：河马兽')).toBeInTheDocument();
    expect(screen.getByText('对方原始文本：火神蛾')).toBeInTheDocument();
    expect(screen.getByText('我方匹配方式：exact')).toBeInTheDocument();
    expect(screen.getByText('对方匹配方式：exact')).toBeInTheDocument();
    expect(screen.getByText(/我方 ROI：/)).toBeInTheDocument();
    expect(screen.getByText(/对方 ROI：/)).toBeInTheDocument();
    expect(screen.getByText('队伍预览')).toBeInTheDocument();
    expect(screen.getByText('已选数量：0')).toBeInTheDocument();
    expect(screen.getByText('指令文本：请选择出3只要上场战斗的宝可梦。')).toBeInTheDocument();
    // "我方队伍" and "对方队伍" appear both in debug panel and in TeamRosterPanel
    expect(screen.getAllByText('我方队伍').length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('对方队伍').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('河马兽')).toBeInTheDocument();
    expect(screen.getByText('火神蛾')).toBeInTheDocument();
    expect(screen.getByText('抓帧方式：ffmpeg-dshow')).toBeInTheDocument();
    expect(screen.getByText('抓帧后端：dshow')).toBeInTheDocument();
    expect(screen.getByText('抓帧错误：ffmpeg_read_failed')).toBeInTheDocument();
    expect(screen.getByText('识别错误：ocr_runtime_error')).toBeInTheDocument();
    expect(screen.getByText('识别错误详情：OneDnnContext does not have the input Filter')).toBeInTheDocument();
    expect(screen.getAllByText('错误详情：device returned no frames').length).toBeGreaterThan(0);
    expect(screen.getByText('FrameVariants')).toBeInTheDocument();
    expect(screen.getByText('局部 ROI 结果')).toBeInTheDocument();

    // Collapse the inner debug panel
    fireEvent.click(screen.getByRole('button', { name: '收起调试面板' }));
    expect(screen.queryByText('布局模板：team_select_default')).not.toBeInTheDocument();
  });
});
