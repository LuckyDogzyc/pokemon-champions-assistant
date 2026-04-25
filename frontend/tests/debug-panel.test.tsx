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

describe('dashboard debug panel', () => {
  it('supports toggling detailed debug info and renders structured evidence, matcher, and team preview details', () => {
    render(<HomePage />);

    expect(screen.getByRole('button', { name: '展开调试面板' })).toBeInTheDocument();
    expect(screen.queryByText('布局模板：team_select_default')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '展开调试面板' }));

    expect(screen.getByRole('button', { name: '收起调试面板' })).toBeInTheDocument();
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
    expect(screen.getByText('我方队伍')).toBeInTheDocument();
    expect(screen.getByText('对方队伍')).toBeInTheDocument();
    expect(screen.getByText('河马兽')).toBeInTheDocument();
    expect(screen.getByText('火神蛾')).toBeInTheDocument();
    expect(screen.getByText('设备来源：opencv · 索引 0 · 当前已选')).toBeInTheDocument();
    expect(screen.getByText('抓帧方式：ffmpeg-dshow')).toBeInTheDocument();
    expect(screen.getByText('抓帧后端：dshow')).toBeInTheDocument();
    expect(screen.getByText('抓帧错误：ffmpeg_read_failed')).toBeInTheDocument();
    expect(screen.getByText('识别错误：ocr_runtime_error')).toBeInTheDocument();
    expect(screen.getByText('识别错误详情：OneDnnContext does not have the input Filter')).toBeInTheDocument();
    expect(screen.getAllByText('错误详情：device returned no frames').length).toBeGreaterThan(0);
    expect(screen.getByText('FrameVariants')).toBeInTheDocument();
    expect(screen.getByText('phase_frame 来源：base-frame-fallback')).toBeInTheDocument();
    expect(screen.getByText('phase_frame 尺寸：640 × 360')).toBeInTheDocument();
    expect(screen.getByText('roi_source_frame 来源：capture.frame_variants.roi_source_frame')).toBeInTheDocument();
    expect(screen.getByText('roi_source_frame 尺寸：1920 × 1080')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'phase_frame 预览' })).toHaveAttribute('src', 'data:image/jpeg;base64,phase-preview');
    expect(screen.getByRole('img', { name: 'roi_source_frame 预览' })).toHaveAttribute('src', 'data:image/jpeg;base64,roi-preview');
    expect(screen.getByText('局部 ROI 结果')).toBeInTheDocument();
    expect(screen.getByText('instruction_banner（phase-detection）')).toBeInTheDocument();
    expect(screen.getByText('选人指令：请选择出3只要上场战斗的宝可梦。 / 选择完毕 / 0/3')).toBeInTheDocument();
    expect(screen.getByText('instruction_banner 来源：phase-frame')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'instruction_banner ROI 预览' })).toHaveAttribute('src', 'data:image/jpeg;base64,instruction-preview');
    expect(screen.getByText('player_team_list（player_team_list）')).toBeInTheDocument();
    expect(screen.getByText('我方队伍块：喷射鸭 / 象牙猪 / 快龙')).toBeInTheDocument();
    expect(screen.getByText('player_team_list 来源：roi-source-frame')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'player_team_list ROI 预览' })).toHaveAttribute('src', 'data:image/jpeg;base64,player-team-preview');
    expect(screen.getByText('opponent_team_list（opponent_team_list）')).toBeInTheDocument();
    expect(screen.getByText('对方队伍块：kubera / 火神蛾 / 西狮海壬')).toBeInTheDocument();
    expect(screen.getByText('opponent_team_list 来源：roi-source-frame')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'opponent_team_list ROI 预览' })).toHaveAttribute('src', 'data:image/jpeg;base64,opponent-team-preview');
    expect(screen.getByText('move_list（battle-move-list）')).toBeInTheDocument();
    expect(screen.getByText('识别条目（4）：日光束 / 魔法闪耀 / 光合作用 / 气象球')).toBeInTheDocument();
    expect(screen.getAllByText('识别方式：ocr-text-list').length).toBeGreaterThanOrEqual(4);
    expect(screen.getByRole('img', { name: 'move_list ROI 预览' })).toHaveAttribute('src', 'data:image/jpeg;base64,move-list-preview');
    const previewImages = screen.getAllByRole('img', { name: '最近抓取截图预览' });
    expect(previewImages).toHaveLength(2);
    previewImages.forEach((image) => {
      expect(image).toHaveAttribute('src', 'data:image/jpeg;base64,debug-preview');
    });

    fireEvent.click(screen.getByRole('button', { name: '收起调试面板' }));
    expect(screen.queryByText('布局模板：team_select_default')).not.toBeInTheDocument();
  });
});
