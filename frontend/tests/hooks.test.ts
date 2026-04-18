import { act, renderHook, waitFor } from '@testing-library/react';

import { useRecognitionPolling } from '../lib/hooks';

jest.mock('../lib/api', () => ({
  getCurrentRecognition: jest.fn(),
  getVideoSources: jest.fn(),
  startRecognitionSession: jest.fn(),
}));

const api = jest.requireMock('../lib/api') as {
  getCurrentRecognition: jest.Mock;
  startRecognitionSession: jest.Mock;
};

describe('useRecognitionPolling', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    api.getCurrentRecognition.mockReset();
    api.startRecognitionSession.mockReset();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it('starts a recognition session before polling current recognition so preview frames can appear', async () => {
    api.startRecognitionSession.mockResolvedValue({
      running: true,
      current_state: {
        current_phase: 'battle',
        player: { confidence: 0, source: 'mock' },
        opponent: { confidence: 0, source: 'mock' },
        preview_image_data_url: 'data:image/jpeg;base64,boot-preview',
      },
    });
    api.getCurrentRecognition.mockResolvedValue({
      current_phase: 'battle',
      player: { confidence: 0.8, source: 'ocr', name: '喷火龙' },
      opponent: { confidence: 0.7, source: 'ocr', name: '皮卡丘' },
      preview_image_data_url: 'data:image/jpeg;base64,poll-preview',
    });

    const { result } = renderHook(() => useRecognitionPolling(3000));

    await waitFor(() => {
      expect(api.startRecognitionSession).toHaveBeenCalledTimes(1);
      expect(result.current.state?.preview_image_data_url).toBe('data:image/jpeg;base64,boot-preview');
    });

    expect(api.getCurrentRecognition).not.toHaveBeenCalled();

    await act(async () => {
      await jest.advanceTimersByTimeAsync(3000);
    });

    await waitFor(() => {
      expect(api.getCurrentRecognition).toHaveBeenCalledTimes(1);
      expect(result.current.state?.preview_image_data_url).toBe('data:image/jpeg;base64,poll-preview');
    });
  });
});
