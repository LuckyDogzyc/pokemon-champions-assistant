import { render, screen } from '@testing-library/react';

import HomePage from '../app/page';

const useRecognitionPollingMock = jest.fn(() => ({
  state: null,
  loading: false,
  refresh: jest.fn(),
  restartSession: jest.fn(),
}));

jest.mock('../lib/hooks', () => ({
  useVideoSources: () => ({
    sources: [],
    loading: false,
    refresh: jest.fn(),
    selectSource: jest.fn(),
  }),
  useRecognitionPolling: (...args: unknown[]) => useRecognitionPollingMock(...args),
}));

describe('Home page', () => {
  beforeEach(() => {
    useRecognitionPollingMock.mockClear();
  });

  it('renders the product title and placeholder recognition status', () => {
    render(<HomePage />);

    expect(
      screen.getByRole('heading', { name: 'Pokemon Champions Assistant' }),
    ).toBeInTheDocument();
    expect(screen.getByText('当前阶段')).toBeInTheDocument();
    expect(screen.getByText('unknown')).toBeInTheDocument();
    expect(screen.getByText('暂无截图')).toBeInTheDocument();
  });

  it('uses 1 second recognition polling on the home page', () => {
    render(<HomePage />);

    expect(useRecognitionPollingMock).toHaveBeenCalledWith(1000);
  });
});
