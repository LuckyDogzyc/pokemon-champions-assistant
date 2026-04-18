import { render, screen } from '@testing-library/react';

import HomePage from '../app/page';

jest.mock('../lib/hooks', () => ({
  useVideoSources: () => ({
    sources: [],
    loading: false,
    refresh: jest.fn(),
  }),
  useRecognitionPolling: () => ({
    state: null,
    loading: false,
    refresh: jest.fn(),
  }),
}));

describe('Home page', () => {
  it('renders the product title and placeholder recognition status', () => {
    render(<HomePage />);

    expect(
      screen.getByRole('heading', { name: 'Pokemon Champions Assistant' }),
    ).toBeInTheDocument();
    expect(screen.getByText('当前阶段')).toBeInTheDocument();
    expect(screen.getByText('unknown')).toBeInTheDocument();
    expect(screen.getByText('暂无截图')).toBeInTheDocument();
  });
});
