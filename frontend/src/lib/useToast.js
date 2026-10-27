import { useCallback, useEffect, useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { clearFlash } from '../features/ui/uiSlice';

/** Toast de la pantalla: { show, message, type }. También muestra el "flash" dejado por la pantalla anterior. */
export default function useToast(duration = 3200) {
  const [toast, setToast] = useState({ show: false, message: '', type: 'success' });
  const timer = useRef(null);
  const flashMsg = useSelector((s) => s.ui.flash);
  const dispatch = useDispatch();

  const show = useCallback(
    (message, type = 'success') => {
      clearTimeout(timer.current);
      setToast({ show: true, message, type });
      timer.current = setTimeout(() => setToast((t) => ({ ...t, show: false })), duration);
    },
    [duration],
  );

  useEffect(() => {
    if (flashMsg) {
      show(flashMsg.message, flashMsg.type);
      dispatch(clearFlash());
    }
  }, [flashMsg, show, dispatch]);

  useEffect(() => () => clearTimeout(timer.current), []);
  return [toast, show];
}
