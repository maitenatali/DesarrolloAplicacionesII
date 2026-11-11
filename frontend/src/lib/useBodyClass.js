import { useEffect } from 'react';

/** Bloquea el scroll del body mientras hay un modal abierto (los mockups lo hacen con overflow:hidden). */
export default function useLockScroll(locked) {
  useEffect(() => {
    if (!locked) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [locked]);
}
