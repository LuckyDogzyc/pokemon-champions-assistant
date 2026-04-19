import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import HomePage from '../app/page';

const selectSourceMock = jest.fn();
const restartRecognitionMock = jest.fn();

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
      {
        id: 'device-1',
        label: 'USB Capture HDMI',
        backend: 'dshow',
        is_selected: false,
        device_kind: 'physical',
      },
    ],
    loading: false,
    refresh: jest.fn(),
    selectSource: selectSourceMock,
  }),
  useRecognitionPolling: () => ({
    state: {
      current_phase: 'battle',
      player_active_name: '喷火龙',
      opponent_active_name: '皮卡丘',
      player: { name: '喷火龙', confidence: 0.98, source: 'ocr' },
      opponent: { name: '皮卡丘', confidence: 0.87, source: 'manual' },
      input_source: 'device-0',
      timestamp: '2026-04-15T15:30:00Z',
      preview_image_data_url: 'data:image/jpeg;base64,dashboard-preview',
      capture_error: 'ffmpeg_read_failed',
      capture_error_detail:
        '[dshow @ 000001] Could not run graph (sometimes caused by a device already in use by other application)',
      capture_help_text:
        '物理采集卡当前可能正被其他程序占用。建议优先在 OBS 中开启 Virtual Camera，并将本助手固定到 OBS Virtual Camera。',
      capture_suggested_source_id: 'device-1',
      capture_suggested_source_label: 'USB Capture HDMI',
    },
    loading: false,
    refresh: jest.fn(),
    restartSession: restartRecognitionMock,
  }),
}));

describe('dashboard page', () => {
  it('renders source selection, phase panel, recognition panels, and linked cards', async () => {
    render(<HomePage />);

    expect(screen.getByRole('combobox', { name: '视频输入源' })).toBeInTheDocument();
    expect(screen.getByText('当前阶段')).toBeInTheDocument();
    expect(screen.getByText('battle')).toBeInTheDocument();
    expect(screen.getByText('我方识别')).toBeInTheDocument();
    expect(screen.getByText('对方识别')).toBeInTheDocument();
    expect(screen.getAllByText('喷火龙').length).toBeGreaterThan(0);
    expect(screen.getAllByText('皮卡丘').length).toBeGreaterThan(0);
    expect(screen.getAllByText('宝可梦资料').length).toBeGreaterThan(0);
    expect(screen.getByText('属性克制摘要')).toBeInTheDocument();
    expect(screen.getByText('默认抓帧频率：每 1 秒 1 帧')).toBeInTheDocument();
    expect(screen.getByText('设备来源：opencv · 虚拟设备 · 当前已选')).toBeInTheDocument();
    expect(
      screen.getByText('建议优先在 OBS 中开启 Virtual Camera，再回到这里确认最近抓取截图是否正确。'),
    ).toBeInTheDocument();
    expect(screen.getByRole('img', { name: '最近抓取截图预览' })).toHaveAttribute(
      'src',
      'data:image/jpeg;base64,dashboard-preview',
    );
    expect(screen.getByText('最近一次抓帧失败：ffmpeg_read_failed')).toBeInTheDocument();
    expect(
      screen.getByText(
        '错误详情：[dshow @ 000001] Could not run graph (sometimes caused by a device already in use by other application)',
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText('物理采集卡当前可能正被其他程序占用。建议优先在 OBS 中开启 Virtual Camera，并将本助手固定到 OBS Virtual Camera。'),
    ).toBeInTheDocument();
    expect(screen.getAllByText('最近抓取截图').length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('button', { name: '切换到 USB Capture HDMI' }));

    await waitFor(() => {
      expect(selectSourceMock).toHaveBeenCalledWith('device-1');
      expect(restartRecognitionMock).toHaveBeenCalledTimes(1);
    });

    fireEvent.change(screen.getByRole('combobox', { name: '视频输入源' }), { target: { value: 'device-0' } });

    await waitFor(() => {
      expect(selectSourceMock).toHaveBeenCalledWith('device-0');
      expect(restartRecognitionMock).toHaveBeenCalledTimes(2);
    });
  });
});
