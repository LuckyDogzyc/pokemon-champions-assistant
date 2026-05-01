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
  useLatestFrame: () => ({
    preview_image_data_url: 'data:image/jpeg;base64,latest-frame',
    width: 1280,
    height: 720,
    capture_error: null,
  }),
}));

jest.mock('../lib/api', () => ({
  searchMoves: jest.fn(() => Promise.resolve({ moves: {} })),
}));

describe('dashboard page', () => {
  it('renders video source selector and battle info panels in new layout', async () => {
    render(<HomePage />);

    // TopBar has the video source selector
    expect(screen.getByRole('combobox', { name: '视频输入源' })).toBeInTheDocument();
    // Debug toggle button
    expect(screen.getByText('调试')).toBeInTheDocument();
    // Center game screen shows the phase
    expect(screen.getByText('battle')).toBeInTheDocument();

    // Selecting a different source via combobox
    fireEvent.change(screen.getByRole('combobox', { name: '视频输入源' }), { target: { value: 'device-1' } });

    await waitFor(() => {
      expect(selectSourceMock).toHaveBeenCalledWith('device-1');
    });
  });
});
