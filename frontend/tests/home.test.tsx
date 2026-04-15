import { render, screen } from '@testing-library/react';

import HomePage from '../app/page';

describe('Home page', () => {
  it('renders the product title and placeholder recognition status', () => {
    render(<HomePage />);

    expect(
      screen.getByRole('heading', { name: 'Pokemon Champions Assistant' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Recognition idle')).toBeInTheDocument();
  });
});
