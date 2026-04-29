import { fireEvent, render, screen } from '@testing-library/react';

import { TopBar } from '../components/top-bar';

describe('TopBar source selection integration', () => {
  it('calls onSelectSource when the user chooses a different input source', () => {
    const onSelectSource = jest.fn();

    render(
      <TopBar
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
        selectedSourceId="4"
        debugOpen={false}
        onToggleDebug={jest.fn()}
        onSelectSource={onSelectSource}
      />,
    );

    // Both sources should be in dropdown
    expect(screen.getByText('OBS Virtual Camera')).toBeInTheDocument();
    expect(screen.getByText('USB Capture HDMI 4K+')).toBeInTheDocument();

    fireEvent.change(screen.getByRole('combobox', { name: '视频输入源' }), { target: { value: '7' } });

    expect(onSelectSource).toHaveBeenCalledWith('7');
  });

  it('toggles debug panel on button click', () => {
    const onToggleDebug = jest.fn();

    render(
      <TopBar
        sources={[
          { id: '4', label: 'OBS Virtual Camera', backend: 'opencv', is_selected: true, device_index: 4 },
        ]}
        selectedSourceId="4"
        debugOpen={false}
        onToggleDebug={onToggleDebug}
        onSelectSource={jest.fn()}
      />,
    );

    // Button shows "调试" when closed
    expect(screen.getByText('调试')).toBeInTheDocument();
    fireEvent.click(screen.getByText('调试'));
    expect(onToggleDebug).toHaveBeenCalledTimes(1);
  });

  it('shows 收起调试 when debug is open', () => {
    render(
      <TopBar
        sources={[
          { id: '4', label: 'OBS Virtual Camera', backend: 'opencv', is_selected: true, device_index: 4 },
        ]}
        selectedSourceId="4"
        debugOpen={true}
        onToggleDebug={jest.fn()}
        onSelectSource={jest.fn()}
      />,
    );

    expect(screen.getByText('收起调试')).toBeInTheDocument();
  });
});
