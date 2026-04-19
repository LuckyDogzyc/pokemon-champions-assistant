import { fireEvent, render, screen } from '@testing-library/react';

import { VideoSourcePanel } from '../components/video-source-panel';

describe('VideoSourcePanel selection', () => {
  it('calls onSelectSource when the user chooses a different input source', () => {
    const onSelectSource = jest.fn();

    render(
      <VideoSourcePanel
        sources={[
          {
            id: '4',
            label: 'OBS Virtual Camera',
            backend: 'opencv',
            is_selected: true,
            device_index: 4,
            device_kind: 'virtual',
          },
          {
            id: '7',
            label: 'USB Capture HDMI 4K+',
            backend: 'opencv',
            is_selected: false,
            device_index: 7,
            device_kind: 'physical',
          },
        ]}
        onSelectSource={onSelectSource}
      />,
    );

    expect(screen.getAllByText(/虚拟设备/i)).toHaveLength(2);
    expect(
      screen.getByText('建议优先在 OBS 中开启 Virtual Camera，再回到这里确认最近抓取截图是否正确。'),
    ).toBeInTheDocument();
    expect(screen.getByText('当前推荐输入：OBS Virtual Camera（OpenCV / 虚拟设备）')).toBeInTheDocument();

    fireEvent.change(screen.getByRole('combobox', { name: '视频输入源' }), { target: { value: '7' } });

    expect(onSelectSource).toHaveBeenCalledWith('7');
  });
});
