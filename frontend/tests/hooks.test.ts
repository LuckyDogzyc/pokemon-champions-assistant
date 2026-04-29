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
    jest.clearAllTimers();
    jest.useRealTimers();
  });

  it('defaults to 2 second polling so recognition can keep up with the real-time target', async () => {
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

    renderHook(() => useRecognitionPolling());

    await waitFor(() => {
      expect(api.startRecognitionSession).toHaveBeenCalledTimes(1);
    });

    expect(api.getCurrentRecognition).not.toHaveBeenCalled();

    await act(async () => {
      await jest.advanceTimersByTimeAsync(2000);
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(api.getCurrentRecognition).toHaveBeenCalledTimes(1);
    });
  });

  it('starts a recognition session before polling current recognition so preview frames can appear', async () => {
    let resolvePoll: ((value: {
      current_phase: string;
      player: { confidence: number; source: string; name: string };
      opponent: { confidence: number; source: string; name: string };
      preview_image_data_url: string;
    }) => void) | null = null;

    api.startRecognitionSession.mockResolvedValue({
      running: true,
      current_state: {
        current_phase: 'battle',
        player: { confidence: 0, source: 'mock' },
        opponent: { confidence: 0, source: 'mock' },
        preview_image_data_url: 'data:image/jpeg;base64,boot-preview',
      },
    });
    api.getCurrentRecognition.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvePoll = resolve;
        }),
    );

    const { result } = renderHook(() => useRecognitionPolling(3000));

    await waitFor(() => {
      expect(api.startRecognitionSession).toHaveBeenCalledTimes(1);
      expect(result.current.state?.preview_image_data_url).toBe('data:image/jpeg;base64,boot-preview');
    });

    expect(api.getCurrentRecognition).not.toHaveBeenCalled();

    await act(async () => {
      await jest.advanceTimersByTimeAsync(3000);
      resolvePoll?.({
        current_phase: 'battle',
        player: { confidence: 0.8, source: 'ocr', name: '喷火龙' },
        opponent: { confidence: 0.7, source: 'ocr', name: '皮卡丘' },
        preview_image_data_url: 'data:image/jpeg;base64,poll-preview',
      });
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(api.getCurrentRecognition).toHaveBeenCalledTimes(1);
      expect(result.current.state?.preview_image_data_url).toBe('data:image/jpeg;base64,poll-preview');
    });
  });

  it('coalesces restart requests while the initial session start is still in flight', async () => {
    let resolveStart: ((value: {
      running: boolean;
      current_state: {
        current_phase: string;
        player: { confidence: number; source: string };
        opponent: { confidence: number; source: string };
      };
    }) => void) | null = null;
    api.startRecognitionSession.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveStart = resolve;
        }),
    );

    const { result } = renderHook(() => useRecognitionPolling(3000));

    await waitFor(() => {
      expect(api.startRecognitionSession).toHaveBeenCalledTimes(1);
    });

    await act(async () => {
      void result.current.restartSession();
      await Promise.resolve();
    });

    expect(api.startRecognitionSession).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolveStart?.({
        running: true,
        current_state: {
          current_phase: 'battle',
          player: { confidence: 0, source: 'mock' },
          opponent: { confidence: 0, source: 'mock' },
        },
      });
      await Promise.resolve();
    });
  });

  it('skips interval polling ticks while a current recognition request is still in flight', async () => {
    let resolvePoll: ((value: {
      current_phase: string;
      player: { confidence: number; source: string };
      opponent: { confidence: number; source: string };
    }) => void) | null = null;
    api.startRecognitionSession.mockResolvedValue({
      running: true,
      current_state: {
        current_phase: 'battle',
        player: { confidence: 0, source: 'mock' },
        opponent: { confidence: 0, source: 'mock' },
      },
    });
    api.getCurrentRecognition.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvePoll = resolve;
        }),
    );

    renderHook(() => useRecognitionPolling(1000));

    await waitFor(() => {
      expect(api.startRecognitionSession).toHaveBeenCalledTimes(1);
    });

    await act(async () => {
      await jest.advanceTimersByTimeAsync(1000);
      await Promise.resolve();
    });
    expect(api.getCurrentRecognition).toHaveBeenCalledTimes(1);

    await act(async () => {
      await jest.advanceTimersByTimeAsync(1000);
      await Promise.resolve();
    });
    expect(api.getCurrentRecognition).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolvePoll?.({
        current_phase: 'battle',
        player: { confidence: 0.8, source: 'ocr' },
        opponent: { confidence: 0.7, source: 'ocr' },
      });
      await Promise.resolve();
    });
  });

  it('waits for an in-flight current poll before restarting a selected source', async () => {
    let resolvePoll: ((value: {
      current_phase: string;
      player: { confidence: number; source: string };
      opponent: { confidence: number; source: string };
    }) => void) | null = null;
    api.startRecognitionSession.mockResolvedValue({
      running: true,
      current_state: {
        current_phase: 'battle',
        player: { confidence: 0, source: 'mock' },
        opponent: { confidence: 0, source: 'mock' },
      },
    });
    api.getCurrentRecognition.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvePoll = resolve;
        }),
    );

    const { result } = renderHook(() => useRecognitionPolling(1000));

    await waitFor(() => {
      expect(api.startRecognitionSession).toHaveBeenCalledTimes(1);
    });

    await act(async () => {
      await jest.advanceTimersByTimeAsync(1000);
      await Promise.resolve();
    });
    expect(api.getCurrentRecognition).toHaveBeenCalledTimes(1);

    let restartPromise: Promise<unknown> | null = null;
    await act(async () => {
      restartPromise = result.current.restartSession();
      await Promise.resolve();
    });
    expect(api.startRecognitionSession).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolvePoll?.({
        current_phase: 'battle',
        player: { confidence: 0.8, source: 'ocr' },
        opponent: { confidence: 0.7, source: 'ocr' },
      });
      await restartPromise;
    });

    expect(api.startRecognitionSession).toHaveBeenCalledTimes(2);
  });
});
