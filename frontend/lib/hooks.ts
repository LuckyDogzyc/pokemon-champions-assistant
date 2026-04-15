import { useCallback, useEffect, useState } from 'react';

import { getCurrentRecognition, getVideoSources } from './api';
import type { RecognitionState, VideoSource } from '../types/api';

export function useVideoSources() {
  const [sources, setSources] = useState<VideoSource[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getVideoSources();
      setSources(data.sources);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { sources, loading, refresh };
}

export function useRecognitionPolling(intervalMs = 3000) {
  const [state, setState] = useState<RecognitionState | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await getCurrentRecognition();
      setState(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => {
      void refresh();
    }, intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs, refresh]);

  return { state, loading, refresh };
}
