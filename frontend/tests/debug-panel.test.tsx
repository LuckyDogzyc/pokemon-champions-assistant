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
    expect(screen.getByRole('img', { name: '最近抓取截图预览' })).toHaveAttribute(
      'src',
      'data:image/jpeg;base64,debug-preview',
    );

    fireEvent.click(screen.getByRole('button', { name: '收起调试面板' }));
    expect(screen.queryByText('布局模板：team_select_default')).not.toBeInTheDocument();
  });
});
