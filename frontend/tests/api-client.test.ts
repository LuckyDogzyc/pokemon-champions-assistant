import {
  getCurrentRecognition,
  getVideoSources,
  overrideRecognition,
  searchPokemon,
  selectVideoSource,
  startRecognitionSession,
} from '../lib/api';

describe('frontend api client', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    jest.resetAllMocks();
  });

  it('calls the expected backend endpoints and parses responses', async () => {
    const fetchMock = jest.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ sources: [{ id: 'device-0', label: 'USB Capture Card' }] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ selected_source_id: 'device-0' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ running: true, current_state: { current_phase: 'battle' } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ current_phase: 'battle', player_active_name: '喷火龙' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ player_active_name: '伊布' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ query: '喷火龙', results: [{ canonical_name: '喷火龙' }] }),
      });

    global.fetch = fetchMock as typeof fetch;

    const sources = await getVideoSources();
    const selected = await selectVideoSource('device-0');
    const started = await startRecognitionSession();
    const current = await getCurrentRecognition();
    const overridden = await overrideRecognition('player', '伊布');
    const search = await searchPokemon('喷火龙');

    expect(sources.sources[0].id).toBe('device-0');
    expect(selected.selected_source_id).toBe('device-0');
    expect(started.running).toBe(true);
    expect(current.player_active_name).toBe('喷火龙');
    expect(overridden.player_active_name).toBe('伊布');
    expect(search.results[0].canonical_name).toBe('喷火龙');

    expect(fetchMock).toHaveBeenNthCalledWith(1, 'http://localhost:8000/api/video/sources', undefined);
    expect(fetchMock).toHaveBeenNthCalledWith(2, 'http://localhost:8000/api/video/source/select', expect.objectContaining({ method: 'POST' }));
    expect(fetchMock).toHaveBeenNthCalledWith(3, 'http://localhost:8000/api/recognition/session/start', expect.objectContaining({ method: 'POST' }));
    expect(fetchMock).toHaveBeenNthCalledWith(4, 'http://localhost:8000/api/recognition/current', undefined);
    expect(fetchMock).toHaveBeenNthCalledWith(5, 'http://localhost:8000/api/recognition/override', expect.objectContaining({ method: 'POST' }));
    expect(fetchMock).toHaveBeenNthCalledWith(6, 'http://localhost:8000/api/pokemon/search?q=%E5%96%B7%E7%81%AB%E9%BE%99', undefined);
  });
});
