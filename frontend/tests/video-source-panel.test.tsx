import { render, screen } from '@testing-library/react';

import { VideoSourcePanel } from '../components/video-source-panel';

describe('VideoSourcePanel', () => {
  it('highlights that physical capture devices are fallback-only and recommends OBS Virtual Camera', () => {
    render(
      <VideoSourcePanel
        sources={[
          {
            id: 'device-0',
            label: 'USB Capture Card',
            backend: 'dshow',
            is_selected: true,
            device_index: 0,
            device_kind: 'physical',
          },
          {
            id: 'device-1',
            label: 'OBS Virtual Camera',
            backend: 'opencv',
            is_selected: false,
            device_index: 1,
            device_kind: 'virtual',
          },
        ]}
      />,
    );

    expect(
      screen.getByText('当前选中的是实体采集设备；正式使用时建议切换到 OBS Virtual Camera，避免和 OBS/其他程序争用物理采集卡。'),
    ).toBeInTheDocument();
  });

  it('explains that users can use the debug panel screenshot preview to confirm the current input source', () => {
    render(
      <VideoSourcePanel
        sources={[
          {
            id: 'device-0',
            label: 'USB Capture Card',
            backend: 'opencv',
            is_selected: true,
            device_index: 0,
          },
        ]}
      />,
    );

    expect(
      screen.getByText('可展开页面下方调试面板，查看最近抓取截图预览来确认当前输入源是否正确。'),
    ).toBeInTheDocument();
  });

  it('warns when the current source still uses a generic Video Device label', () => {
    render(
      <VideoSourcePanel
        sources={[
          {
            id: 'device-2',
            label: 'Video Device 2',
            backend: 'opencv',
            is_selected: true,
            device_index: 2,
          },
        ]}
      />,
    );

    expect(
      screen.getByText('当前名称仍是系统索引占位名（如 Video Device 2），可结合下方截图预览确认它对应的是哪一路画面。'),
    ).toBeInTheDocument();
  });
});
