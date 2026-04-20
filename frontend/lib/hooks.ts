'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { getCurrentRecognition, getVideoSources, selectVideoSource, startRecognitionSession } from './api';
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

  const selectSource = useCallback(
    async (sourceId: string) => {
      await selectVideoSource(sourceId);
      await refresh();
    },
    [refresh],
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { sources, loading, refresh, selectSource };
}

export function useRecognitionPolling(intervalMs = 1000) {
  const [state, setState] = useState<RecognitionState | null>(null);
  const [loading, setLoading] = useState(true);
  const sessionStartedRef = useRef(false);

  const restartSession = useCallback(async () => {
    setLoading(true);
    try {
      const started = await startRecognitionSession();
      sessionStartedRef.current = true;
      setState(started.current_state ?? null);
      return started.current_state ?? null;
    } finally {
      setLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    try {
      if (!sessionStartedRef.current) {
        await restartSession();
        return;
      }

      const data = await getCurrentRecognition();
      setState(data);
    } finally {
      setLoading(false);
    }
  }, [restartSession]);

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => {
      void refresh();
    }, intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs, refresh]);

  return { state, loading, refresh, restartSession };
}
