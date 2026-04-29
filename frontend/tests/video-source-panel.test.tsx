import { fireEvent, render, screen } from '@testing-library/react';

import { TopBar } from '../components/top-bar';

describe('TopBar video source selection', () => {
  it('renders all sources in the select dropdown', () => {
    const onSelect = jest.fn();
    render(
      <TopBar
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
        selectedSourceId="device-0"
        debugOpen={false}
        onToggleDebug={jest.fn()}
        onSelectSource={onSelect}
      />,
    );

    expect(screen.getByRole('combobox', { name: '视频输入源' })).toBeInTheDocument();
    expect(screen.getByText('USB Capture Card')).toBeInTheDocument();
    expect(screen.getByText('OBS Virtual Camera')).toBeInTheDocument();
  });

  it('shows the placeholder when no sources are available', () => {
    render(
      <TopBar
        sources={[]}
        selectedSourceId=""
        debugOpen={false}
        onToggleDebug={jest.fn()}
        onSelectSource={jest.fn()}
      />,
    );

    expect(screen.getByText('未检测到输入源')).toBeInTheDocument();
  });

  it('calls onSelectSource when user chooses a different source', () => {
    const onSelect = jest.fn();
    render(
      <TopBar
        sources={[
          {
            id: 'device-0',
            label: 'USB Capture Card',
            backend: 'opencv',
            is_selected: true,
            device_index: 0,
          },
        ]}
        selectedSourceId="device-0"
        debugOpen={false}
        onToggleDebug={jest.fn()}
        onSelectSource={onSelect}
      />,
    );

    fireEvent.change(screen.getByRole('combobox', { name: '视频输入源' }), { target: { value: 'device-0' } });
    expect(onSelect).toHaveBeenCalledWith('device-0');
  });
});
