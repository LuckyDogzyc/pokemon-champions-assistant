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
  useLatestFrame: () => ({
    preview_image_data_url: null,
    width: null,
    height: null,
    capture_error: null,
  }),
}));

jest.mock('../lib/api', () => ({
  searchMoves: jest.fn(() => Promise.resolve({ moves: {} })),
}));

describe('Home page', () => {
  beforeEach(() => {
    useRecognitionPollingMock.mockClear();
  });

  it('renders the brand name and video source selector', () => {
    render(<HomePage />);

    expect(screen.getByText('Pokémon Champions Assistant')).toBeInTheDocument();
    expect(screen.getByLabelText('视频输入源')).toBeInTheDocument();
  });

  it('shows game screen placeholder when no preview available', () => {
    render(<HomePage />);
    expect(screen.getByText('暂无画面')).toBeInTheDocument();
  });

  it('uses 2 second recognition polling on the home page', () => {
    render(<HomePage />);

    expect(useRecognitionPollingMock).toHaveBeenCalledWith(2000);
  });
});
