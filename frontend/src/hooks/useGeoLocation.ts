import { useState, useEffect } from 'react';

interface GeoState {
  lat: number | null;
  lon: number | null;
  error: string | null;
  loading: boolean;
  request: () => void;
}

export function useGeoLocation(): GeoState {
  const [lat, setLat]         = useState<number | null>(null);
  const [lon, setLon]         = useState<number | null>(null);
  const [error, setError]     = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const request = () => {
    if (!navigator.geolocation) {
      setError('Géolocalisation non supportée');
      return;
    }
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude);
        setLon(pos.coords.longitude);
        setLoading(false);
      },
      (err) => {
        setError(err.message);
        setLoading(false);
      }
    );
  };

  return { lat, lon, error, loading, request };
}
