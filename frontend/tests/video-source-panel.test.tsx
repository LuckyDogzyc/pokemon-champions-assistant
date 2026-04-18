import { render, screen } from '@testing-library/react';

import { VideoSourcePanel } from '../components/video-source-panel';

describe('VideoSourcePanel', () => {
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
