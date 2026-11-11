import { useNavigate, useParams } from 'react-router-dom';
import { useGetPurchasesQuery } from '../api/api';
import AppShell, { useCurrentTeacher } from '../components/AppShell';
import * as I from '../components/icons.generated';
import { isoLongDate, isoShortDate, isoTime, money } from '../lib/format';
import { purchaseCode } from '../lib/purchases';
import '../styles/pages/23.css';

export default function PurchaseDetail() {
  const navigate = useNavigate();
  const { purchaseId } = useParams();
  const { data, isLoading } = useGetPurchasesQuery();
  const { me, fullName } = useCurrentTeacher();
  const p = (data || []).find((x) => x.purchaseId === purchaseId);

  const head = (
    <>
      <p className="breadcrumb">
        <a href="/" onClick={(e) => (e.preventDefault(), navigate('/'))}>
          Inicio
        </a>{' '}
        /{' '}
        <a href="/compras" onClick={(e) => (e.preventDefault(), navigate('/compras'))}>
          Mis compras
        </a>{' '}
        / <span className="current">Detalle de compra</span>
      </p>
      <button className="back-link" onClick={() => navigate('/compras')}>
        <I.i105 />
        Volver a mis compras
      </button>
    </>
  );

  if (!p) {
    return (
      <AppShell scope="23" active="compras">
        {head}
        <div className="panel">
          <div className="panel-body">{isLoading ? <div className="skel" style={{ width: '100%', height: 120 }} /> : 'No encontramos esa compra.'}</div>
        </div>
      </AppShell>
    );
  }

  const subtotal = p.items.reduce((s, it) => s + Number(it.subtotal), 0);
  const charge = Math.max(0, Number(p.total) - subtotal);
  const discount = Math.max(0, subtotal - Number(p.total));

  return (
    <AppShell scope="23" active="compras">
      {head}
      <div>
        <div className="notif-top-row">
          <div>
            <h1 className="page-title">Detalle de compra</h1>
            <p className="purchase-sub">Compra {purchaseCode(p)}</p>
            <span className="purchase-datetime">
              {isoLongDate(p.createdAt)} · {isoTime(p.createdAt)}
            </span>
          </div>
        </div>
        <div className="detail-layout">
          <div>
            <div className="panel">
              <div className="panel-head">
                <h2 className="panel-title">Productos / servicios</h2>
              </div>
              <div className="panel-body">
                {p.items.map((it) => (
                  <div className="line-item" key={it.productId}>
                    <span className="line-item-icon">
                      <I.i21 />
                    </span>
                    <div className="line-item-main">
                      <p className="line-item-name">{it.productName}</p>
                      <div className="line-item-qty-row">
                        <span>Cantidad: {it.quantity}</span>
                      </div>
                    </div>
                    <div className="line-item-price">
                      <p className="line-item-unit">Precio unitario: {money(it.unitPrice)}</p>
                      <p className="line-item-subtotal">{money(it.subtotal)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div>
            <div className="panel">
              <div className="panel-head">
                <h2 className="panel-title">Resumen</h2>
              </div>
              <div className="panel-body">
                <div className="summary-row">
                  <span className="summary-label">Subtotal</span>
                  <span className="summary-value">{money(subtotal)}</span>
                </div>
                <div className={`summary-row${discount > 0 ? ' discount' : ''}`}>
                  <span className="summary-label">Descuento</span>
                  <span className="summary-value">{discount > 0 ? `-${money(discount)}` : '$0'}</span>
                </div>
                <div className="summary-row">
                  <span className="summary-label">Cargo adicional</span>
                  <span className="summary-value">{money(charge)}</span>
                </div>
                <div className="summary-divider" />
                <div className="summary-row total">
                  <span className="summary-label">Total</span>
                  <span className="summary-value">{money(p.total)}</span>
                </div>
              </div>
            </div>
            <div className="panel">
              <div className="panel-head">
                <h2 className="panel-title">Medio de pago</h2>
              </div>
              <div className="panel-body">
                <div className="payment-row">
                  <span className="payment-icon">
                    <I.i15 />
                  </span>
                  <div>
                    <p className="payment-main-text">Cuenta institucional</p>
                    <p className="payment-sub-text">Débito de saldo UADEnet ({p.currency})</p>
                  </div>
                </div>
              </div>
            </div>
            <div className="panel">
              <div className="panel-head">
                <h2 className="panel-title">Información de la transacción</h2>
              </div>
              <div className="panel-body">
                <div className="meta-list">
                  <div className="meta-row">
                    <span className="meta-label">Número de compra</span>
                    <span className="meta-value">{purchaseCode(p)}</span>
                  </div>
                  <div className="meta-row">
                    <span className="meta-label">Fecha</span>
                    <span className="meta-value">{isoShortDate(p.createdAt)}</span>
                  </div>
                  <div className="meta-row">
                    <span className="meta-label">Hora</span>
                    <span className="meta-value">{isoTime(p.createdAt)}</span>
                  </div>
                </div>
              </div>
            </div>
            <div className="panel">
              <div className="panel-head">
                <h2 className="panel-title">Datos del comprador</h2>
              </div>
              <div className="panel-body">
                <div className="meta-list">
                  <div className="meta-row">
                    <span className="meta-label">Nombre</span>
                    <span className="meta-value">{fullName}</span>
                  </div>
                  <div className="meta-row">
                    <span className="meta-label">Usuario</span>
                    <span className="meta-value">{me?.email?.split('@')[0]}</span>
                  </div>
                  <div className="meta-row">
                    <span className="meta-label">Correo</span>
                    <span className="meta-value">{me?.email}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
