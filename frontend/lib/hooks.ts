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

export function useRecognitionPolling(intervalMs = 2000) {
  const [state, setState] = useState<RecognitionState | null>(null);
  const [loading, setLoading] = useState(true);
  const sessionStartedRef = useRef(false);
  const requestInFlightRef = useRef<Promise<RecognitionState | null> | null>(null);
  const requestKindRef = useRef<'start' | 'current' | null>(null);

  const runExclusive = useCallback((kind: 'start' | 'current', operation: () => Promise<RecognitionState | null>) => {
    if (requestInFlightRef.current) {
      return requestInFlightRef.current;
    }

    requestKindRef.current = kind;
    const pending = operation().finally(() => {
      if (requestInFlightRef.current === pending) {
        requestInFlightRef.current = null;
        requestKindRef.current = null;
      }
    });
    requestInFlightRef.current = pending;
    return pending;
  }, []);

  const restartSession = useCallback(async () => {
    if (requestInFlightRef.current && requestKindRef.current === 'current') {
      await requestInFlightRef.current;
    }

    return runExclusive('start', async () => {
      setLoading(true);
      try {
        const started = await startRecognitionSession();
        sessionStartedRef.current = true;
        const nextState = started.current_state ?? null;
        setState(nextState);
        return nextState;
      } finally {
        setLoading(false);
      }
    });
  }, [runExclusive]);

  const refresh = useCallback(async () => {
    if (requestInFlightRef.current) {
      return requestInFlightRef.current;
    }

    if (!sessionStartedRef.current) {
      return runExclusive('start', async () => {
        try {
          const started = await startRecognitionSession();
          sessionStartedRef.current = true;
          const nextState = started.current_state ?? null;
          setState(nextState);
          return nextState;
        } finally {
          setLoading(false);
        }
      });
    }

    return runExclusive('current', async () => {
      try {
        const data = await getCurrentRecognition();
        setState(data);
        return data;
      } finally {
        setLoading(false);
      }
    });
  }, [runExclusive]);

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => {
      void refresh();
    }, intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs, refresh]);

  return { state, loading, refresh, restartSession };
}

// Removed: useLatestFrame — real-time game screen preview no longer shown in center panel.
