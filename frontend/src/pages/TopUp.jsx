import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGetWalletQuery, useTopUpMutation } from '../api/api';
import { toApiError } from '../api/baseQuery';
import AppShell, { useCurrentTeacher } from '../components/AppShell';
import * as I from '../components/icons.generated';
import { money, uuid } from '../lib/format';
import useLockScroll from '../lib/useBodyClass';
import '../styles/pages/26.css';

const MIN_AMOUNT = 5000;
const MAX_AMOUNT = 100000;
const PRESETS = [5000, 10000, 20000, 50000];

/**
 * Medio de pago simulado (CORE mock): la tarjeta nunca sale del navegador; a CORE solo va un token.
 * Tarjetas de prueba: terminada en 0002 = rechazada, en 0004 = queda pendiente; cualquier otra = aprobada.
 */
function paymentToken(method, cardNumber) {
  if (method !== 'newcard') return 'mock-approved';
  const digits = cardNumber.replace(/\D/g, '');
  if (digits.endsWith('0002')) return 'mock-rejected';
  if (digits.endsWith('0004')) return 'mock-pending';
  return 'mock-approved';
}

function cardErrors(card) {
  const e = {};
  if (!/^\d{16}$/.test(card.number.replace(/\s/g, ''))) e.number = true;
  if (!card.holder.trim()) e.holder = true;
  const m = card.expiry.match(/^(\d{2})\/(\d{2})$/);
  let expInvalid = !m;
  if (m) {
    const mm = Number(m[1]);
    const yy = Number(m[2]);
    const now = new Date();
    const curYY = now.getFullYear() % 100;
    expInvalid = mm < 1 || mm > 12 || yy < curYY || (yy === curYY && mm < now.getMonth() + 1);
  }
  if (expInvalid) e.expiry = true;
  if (!/^\d{3}$/.test(card.cvv)) e.cvv = true;
  return e;
}

export default function TopUp() {
  const navigate = useNavigate();
  const { fullName } = useCurrentTeacher();
  const wallet = useGetWalletQuery();
  const [topUp] = useTopUpMutation();
  const [preset, setPreset] = useState(10000);
  const [custom, setCustom] = useState('');
  const [method, setMethod] = useState('saved');
  const [card, setCard] = useState({ number: '', holder: '', expiry: '', cvv: '' });
  const [cardErr, setCardErr] = useState({});
  const [terms, setTerms] = useState(false);
  const [modal, setModal] = useState(null); // terms | cancel | {state, ...}
  useLockScroll(!!modal);

  const current = Number(wallet.data?.balance || 0);
  let amount = preset;
  let amountError = null;
  if (custom.trim() !== '') {
    const n = Number(custom.replace(/\./g, '').replace(',', '.'));
    if (Number.isNaN(n) || n <= 0) amountError = 'Ingresá un importe válido.';
    else if (n < MIN_AMOUNT) amountError = `El importe mínimo de carga es ${money(MIN_AMOUNT)}.`;
    else if (n > MAX_AMOUNT) amountError = `El importe máximo de carga es ${money(MAX_AMOUNT)}.`;
    amount = amountError ? 0 : Math.round(n * 100) / 100;
  }
  const digits = card.number.replace(/\D/g, '');
  const methodLabel = method === 'saved' ? 'Visa •••• 4521' : digits ? `Nueva tarjeta •••• ${digits.slice(-4)}` : 'Nueva tarjeta';
  const canConfirm = amount >= MIN_AMOUNT && amount <= MAX_AMOUNT && terms;

  const setCardField = (field, value) => setCard((c) => ({ ...c, [field]: value }));

  const confirm = async () => {
    if (!canConfirm) return;
    if (method === 'newcard') {
      const e = cardErrors(card);
      setCardErr(e);
      if (Object.keys(e).length) return;
    }
    const previous = current;
    setModal({ state: 'processing' });
    try {
      const tx = await topUp({
        idempotencyKey: uuid(),
        amount: amount.toFixed(2),
        currency: 'ARS',
        paymentMethodToken: paymentToken(method, card.number),
      }).unwrap();
      setModal({ state: tx.status === 'PENDING' ? 'pendiente' : 'exito', tx, previous });
    } catch (err) {
      const e = toApiError(err);
      setModal({ state: e.code === 'WALLET_TOPUP_REJECTED' ? 'errorpago' : 'error', detail: e.detail });
    }
  };

  const goAccount = () => navigate('/cuenta');
  const opNumber = (tx) => `MOV-${tx.transactionId.slice(0, 8).toUpperCase()}`;
  const st = typeof modal === 'object' && modal ? modal.state : null;

  let processCard = null;
  if (st === 'processing') {
    processCard = (
      <>
        <div className="modal-body">
          <div className="processing-spinner" />
          <p className="modal-title">Procesando carga...</p>
          <p className="modal-text">Estamos procesando tu pago y actualizando tu cuenta institucional.</p>
        </div>
        <div className="modal-foot" />
      </>
    );
  } else if (st === 'exito') {
    processCard = (
      <>
        <div className="modal-body">
          <span className="modal-icon success">
            <I.i47 />
          </span>
          <p className="modal-title">¡Saldo cargado correctamente!</p>
          <p className="modal-text">La carga fue procesada correctamente y el saldo ya está disponible.</p>
          <div className="modal-meta-box">
            <div className="mm-row">
              <span>Importe cargado</span>
              <span>+{money(modal.tx.amount)}</span>
            </div>
            <div className="mm-row">
              <span>Saldo anterior</span>
              <span>{money(modal.previous)}</span>
            </div>
            <div className="mm-row">
              <span>Nuevo saldo</span>
              <span>{money(modal.tx.balanceAfter)}</span>
            </div>
            <div className="mm-row">
              <span>Medio de pago</span>
              <span>{methodLabel}</span>
            </div>
            <div className="mm-row">
              <span>N.º de operación</span>
              <span>{opNumber(modal.tx)}</span>
            </div>
          </div>
        </div>
        <div className="modal-foot">
          <button className="btn-primary" onClick={goAccount}>
            Ver cuenta institucional
          </button>
        </div>
      </>
    );
  } else if (st === 'pendiente') {
    processCard = (
      <>
        <div className="modal-body">
          <span className="modal-icon info">
            <I.i112 />
          </span>
          <p className="modal-title">Carga pendiente</p>
          <p className="modal-text">La solicitud fue registrada, pero todavía estamos esperando la confirmación del pago.</p>
          <div className="modal-meta-box">
            <div className="mm-row">
              <span>Importe</span>
              <span>+{money(modal.tx.amount)}</span>
            </div>
            <div className="mm-row">
              <span>N.º de operación</span>
              <span>{opNumber(modal.tx)}</span>
            </div>
            <div className="mm-row">
              <span>Estado</span>
              <span>Pendiente</span>
            </div>
          </div>
        </div>
        <div className="modal-foot">
          <button className="btn-primary" onClick={goAccount}>
            Ver cuenta institucional
          </button>
        </div>
      </>
    );
  } else if (st === 'errorpago') {
    processCard = (
      <>
        <div className="modal-body">
          <span className="modal-icon error">
            <I.i53 />
          </span>
          <p className="modal-title">No pudimos procesar la carga</p>
          <p className="modal-text">El medio de pago seleccionado fue rechazado.</p>
        </div>
        <div className="modal-foot">
          <button
            className="btn-primary"
            onClick={() => {
              setModal(null);
              document.getElementById('payNewCard')?.scrollIntoView({ behavior: 'smooth' });
            }}
          >
            Cambiar medio de pago
          </button>
          <button className="btn-secondary" onClick={confirm}>
            Intentar nuevamente
          </button>
        </div>
      </>
    );
  } else if (st === 'error') {
    processCard = (
      <>
        <div className="modal-body">
          <span className="modal-icon error">
            <I.i53 />
          </span>
          <p className="modal-title">Ocurrió un problema</p>
          <p className="modal-text">{modal.detail || 'No pudimos completar la carga de saldo. Intentá nuevamente.'}</p>
        </div>
        <div className="modal-foot">
          <button className="btn-primary" onClick={confirm}>
            Intentar nuevamente
          </button>
          <button className="btn-secondary" onClick={() => setModal(null)}>
            Cancelar
          </button>
        </div>
      </>
    );
  }

  const modals = (
    <>
      <div className={`modal-backdrop${modal === 'terms' ? ' show' : ''}`} onClick={(e) => e.target === e.currentTarget && setModal(null)}>
        <div className="modal-card" style={{ maxWidth: '480px' }}>
          <div className="modal-body" style={{ textAlign: 'left' }}>
            <p className="modal-title" style={{ textAlign: 'left' }}>
              Términos y condiciones de la carga de saldo
            </p>
            <p className="modal-text">
              El saldo cargado a la cuenta institucional es de uso exclusivo dentro de la tienda virtual de UADEnet para la adquisición de
              productos de la misma.
            </p>
          </div>
          <div className="modal-foot">
            <button className="btn-primary" onClick={() => setModal(null)}>
              Entendido
            </button>
          </div>
        </div>
      </div>
      <div className={`modal-backdrop${modal === 'cancel' ? ' show' : ''}`} onClick={(e) => e.target === e.currentTarget && setModal(null)}>
        <div className="modal-card">
          <div className="modal-body">
            <span className="modal-icon warn">
              <I.i53 />
            </span>
            <p className="modal-title">¿Cancelar carga?</p>
            <p className="modal-text">Los datos ingresados se perderán.</p>
          </div>
          <div className="modal-foot">
            <button className="btn-primary" onClick={() => setModal(null)}>
              Continuar
            </button>
            <button className="btn-danger-ghost" onClick={goAccount}>
              Cancelar carga
            </button>
          </div>
        </div>
      </div>
      <div className={`modal-backdrop${st ? ' show' : ''}`}>
        <div className="modal-card">{processCard}</div>
      </div>
    </>
  );

  return (
    <AppShell scope="26" active="cuenta" after={modals}>
      <button className="back-link" onClick={goAccount}>
        <I.i33 />
        Volver a cuenta
      </button>
      <p className="breadcrumb">
        <a href="/" onClick={(e) => (e.preventDefault(), navigate('/'))}>
          Inicio
        </a>{' '}
        /{' '}
        <a href="/cuenta" onClick={(e) => (e.preventDefault(), goAccount())}>
          Cuenta institucional
        </a>{' '}
        / <span className="current">Cargar saldo</span>
      </p>
      <div className="page-head">
        <h1>Cargar saldo</h1>
        <p>Agregá saldo a tu cuenta institucional para utilizarlo en tus compras en la tienda virtual.</p>
      </div>
      <div className="current-balance-card">
        <div className="cb-left">
          <span className="cb-icon">
            <I.i110 />
          </span>
          <div>
            <p className="cb-label">Saldo actual</p>
            <p className="cb-amount">{wallet.data ? money(current) : '…'}</p>
            <p className="cb-sub">Disponible para utilizar</p>
          </div>
        </div>
      </div>
      <div className="load-grid">
        <div className="form-col">
          <div className="panel">
            <div className="panel-head">
              <p className="panel-eyebrow">¿Cuánto querés cargar?</p>
            </div>
            <div className="panel-body">
              <div className="amount-grid">
                {PRESETS.map((v) => (
                  <button
                    key={v}
                    className={`amount-option${custom === '' && preset === v ? ' selected' : ''}`}
                    onClick={() => {
                      setPreset(v);
                      setCustom('');
                    }}
                  >
                    {money(v)}
                  </button>
                ))}
              </div>
              <p className="field-label">Otro importe</p>
              <div className="custom-amount-wrap">
                <span className="curr-prefix">$</span>
                <input
                  type="text"
                  inputMode="decimal"
                  className={`custom-amount-input${amountError ? ' invalid' : ''}`}
                  placeholder="Ingresá un importe"
                  value={custom}
                  onChange={(e) => setCustom(e.target.value)}
                />
              </div>
              <div className="field-error" style={{ display: amountError ? 'flex' : 'none' }}>
                <I.i3 />
                <span>{amountError}</span>
              </div>
              <p className="field-hint">
                Importe mínimo de carga: {money(MIN_AMOUNT)}. Importe máximo: {money(MAX_AMOUNT)}.
              </p>
            </div>
          </div>
          <div className="panel">
            <div className="panel-head">
              <p className="panel-eyebrow">Medio de pago</p>
            </div>
            <div className="panel-body">
              <div className="pay-option">
                <input
                  type="radio"
                  name="payMethod"
                  id="paySavedCard"
                  value="saved"
                  checked={method === 'saved'}
                  onChange={() => setMethod('saved')}
                />
                <div className="pay-option-main">
                  <label className="pay-option-label" htmlFor="paySavedCard">
                    Visa •••• 4521
                  </label>
                  <p className="pay-option-sub">{fullName}</p>
                </div>
              </div>
              <div className="pay-option">
                <input
                  type="radio"
                  name="payMethod"
                  id="payNewCard"
                  value="newcard"
                  checked={method === 'newcard'}
                  onChange={() => setMethod('newcard')}
                />
                <label className="pay-option-label" htmlFor="payNewCard">
                  Otra tarjeta
                </label>
              </div>
              <div className={`new-card-form${method === 'newcard' ? ' show' : ''}`}>
                <div className="card-form-row">
                  <div className="card-field">
                    <label htmlFor="cardNumber">Número de tarjeta</label>
                    <input
                      type="text"
                      id="cardNumber"
                      placeholder="1234 5678 9012 3456"
                      maxLength={19}
                      autoComplete="off"
                      className={cardErr.number ? 'invalid' : ''}
                      value={card.number}
                      onChange={(e) =>
                        setCardField(
                          'number',
                          e.target.value
                            .replace(/\D/g, '')
                            .slice(0, 16)
                            .replace(/(.{4})/g, '$1 ')
                            .trim(),
                        )
                      }
                    />
                    <span className="card-error" style={{ display: cardErr.number ? 'block' : 'none' }}>
                      Número de tarjeta inválido.
                    </span>
                  </div>
                </div>
                <div className="card-form-row">
                  <div className="card-field">
                    <label htmlFor="cardHolder">Nombre del titular</label>
                    <input
                      type="text"
                      id="cardHolder"
                      placeholder="Nombre y apellido"
                      className={cardErr.holder ? 'invalid' : ''}
                      value={card.holder}
                      onChange={(e) => setCardField('holder', e.target.value.replace(/[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s]/g, ''))}
                    />
                    <span className="card-error" style={{ display: cardErr.holder ? 'block' : 'none' }}>
                      Ingresá el nombre del titular.
                    </span>
                  </div>
                </div>
                <div className="card-form-row two">
                  <div className="card-field">
                    <label htmlFor="cardExpiry">Fecha de vencimiento</label>
                    <input
                      type="text"
                      id="cardExpiry"
                      placeholder="MM/AA"
                      maxLength={5}
                      className={cardErr.expiry ? 'invalid' : ''}
                      value={card.expiry}
                      onChange={(e) => {
                        let d = e.target.value.replace(/\D/g, '').slice(0, 4);
                        if (d.length > 2) d = `${d.slice(0, 2)}/${d.slice(2)}`;
                        setCardField('expiry', d);
                      }}
                    />
                    <span className="card-error" style={{ display: cardErr.expiry ? 'block' : 'none' }}>
                      La tarjeta está vencida.
                    </span>
                  </div>
                  <div className="card-field">
                    <div className="cvv-label-row">
                      <label htmlFor="cardCvv" style={{ marginBottom: '0' }}>
                        Código de seguridad
                      </label>
                      <I.i111 />
                    </div>
                    <input
                      type="password"
                      id="cardCvv"
                      placeholder="•••"
                      maxLength={3}
                      inputMode="numeric"
                      autoComplete="off"
                      className={cardErr.cvv ? 'invalid' : ''}
                      value={card.cvv}
                      onChange={(e) => setCardField('cvv', e.target.value.replace(/\D/g, ''))}
                    />
                    <span className="card-error" style={{ display: cardErr.cvv ? 'block' : 'none' }}>
                      Ingresá el código de seguridad.
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="summary-col">
          <div className="panel">
            <div className="panel-head">
              <p className="panel-eyebrow">Resumen</p>
            </div>
            <div className="panel-body">
              <div className="summary-line">
                <span>Saldo actual</span>
                <span>{money(current)}</span>
              </div>
              <div className="summary-line">
                <span>Carga de saldo</span>
                <span>+{money(amount)}</span>
              </div>
              <div className="summary-divider" />
              <div className="summary-total">
                <span>Total a pagar</span>
                <span>{money(amount)}</span>
              </div>
              <div className="new-balance-box">
                <span className="nb-label">Nuevo saldo</span>
                <span className="nb-value">{money(current + amount)}</span>
              </div>
              <div className="summary-method">
                Medio de pago
                <strong>{methodLabel}</strong>
              </div>
              <div className="terms-row">
                <input type="checkbox" id="termsCheck" checked={terms} onChange={(e) => setTerms(e.target.checked)} />
                <label htmlFor="termsCheck">
                  Acepto los{' '}
                  <button type="button" className="terms-link" onClick={() => setModal('terms')}>
                    términos y condiciones
                  </button>{' '}
                  de la carga de saldo.
                </label>
              </div>
              <div className="order-actions">
                <button className="btn-primary" disabled={!canConfirm} onClick={confirm}>
                  <I.i45 />
                  <span>Confirmar carga — {money(amount)}</span>
                </button>
                <button className="btn-secondary" onClick={() => setModal('cancel')}>
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
