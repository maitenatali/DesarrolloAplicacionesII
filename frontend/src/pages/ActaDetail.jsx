import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAnnulActaMutation, useGetActaQuery, useSyncActaMutation } from '../api/api';
import { toApiError } from '../api/baseQuery';
import AppShell from '../components/AppShell';
import * as I from '../components/icons.generated';
import { RESULT_LABEL } from '../lib/domain';
import { grade, isoShortDate, isoTime, longDate, shortDate } from '../lib/format';
import useLockScroll from '../lib/useBodyClass';
import useToast from '../lib/useToast';
import '../styles/pages/17.css';

const NAME = { FINAL: 'Acta Final', CURSADA: 'Acta de Cursada' };
const CELL = { APROBADO: 'aprobado', REGULAR: 'aprobado', DESAPROBADO: 'desaprobado', LIBRE: 'desaprobado', AUSENTE: 'ausente' };

function Sheet({ acta }) {
  const c = acta.counts || {};
  return (
    <article className="acta-sheet" aria-label="Vista previa del acta académica">
      <div className="sheet-institutional">
        <div className="sheet-mark">
          <I.i87 />
        </div>
        <p className="sheet-univ">UADE</p>
        <p className="sheet-univ-full">Universidad Argentina de la Empresa</p>
      </div>
      <p className="sheet-doc-type">Acta académica</p>
      <h2 className="sheet-doc-title">{NAME[acta.type].toUpperCase()}</h2>
      <p className="sheet-doc-number">N.º {acta.number}</p>
      <div className="sheet-data-grid">
        {[
          ['Curso', acta.subject],
          ['Comisión', acta.commission],
          ['Período', acta.period],
          ['Fecha', longDate(acta.date)],
          ['Docente', acta.teacherName],
        ].map(([k, v]) => (
          <div className="sheet-data-item" key={k}>
            <span className="k">{k}</span>
            <span className="v">{v}</span>
          </div>
        ))}
      </div>
      <p className="sheet-table-title">Resultados académicos</p>
      <table className="sheet-table">
        <thead>
          <tr>
            <th>N.º</th>
            <th>Estudiante</th>
            <th>Legajo</th>
            <th>Resultado</th>
            <th>Condición</th>
          </tr>
        </thead>
        <tbody>
          {(acta.rows || []).map((r) => (
            <tr key={r.studentId}>
              <td>{r.order}</td>
              <td>{r.studentName}</td>
              <td>{r.studentFileNumber}</td>
              <td>{grade(r.grade)}</td>
              <td>
                <span className={`cell-badge ${CELL[r.result] || 'ausente'}`}>{RESULT_LABEL[r.result] || r.result}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="sheet-total">Total de estudiantes: {(acta.rows || []).length}</p>
      <p className="sheet-summary">
        {acta.type === 'FINAL'
          ? `${c.approved || 0} aprobados · ${c.failed || 0} desaprobados · ${c.absent || 0} ausentes`
          : `${c.regular || 0} regulares · ${c.free || 0} libres`}
      </p>
      <p className="sheet-obs-title">Observaciones</p>
      <p className="sheet-obs-text">{acta.notes || 'Sin observaciones.'}</p>
      <div className="sheet-signature">
        <div className="sig-line" />
        <p className="sig-name">{acta.teacherName}</p>
        <p className="sig-role">Docente responsable</p>
        <span className="sig-time">
          {isoShortDate(acta.generatedAt)} · {isoTime(acta.generatedAt)}
        </span>
      </div>
    </article>
  );
}

export default function ActaDetail() {
  const navigate = useNavigate();
  const { actaId } = useParams();
  const { data: acta, isLoading, error, refetch } = useGetActaQuery(actaId);
  const [annul, annulState] = useAnnulActaMutation();
  const [sync, syncState] = useSyncActaMutation();
  const [overlay, setOverlay] = useState(false);
  const [annulOpen, setAnnulOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [toast, showToast] = useToast(2800);
  useLockScroll(overlay);

  const crumbs = (label) => (
    <p className="breadcrumb">
      <button className="bc-link" onClick={() => navigate('/')}>
        Inicio
      </button>
      <span className="sep">/</span>
      <button className="bc-link" onClick={() => navigate('/actas')}>
        Actas
      </button>
      <span className="sep">/</span>
      <span className="current">{label}</span>
    </p>
  );

  if (!acta) {
    const err = toApiError(error);
    return (
      <AppShell scope="17" active="actas">
        {crumbs('Acta')}
        <div className="panel">
          <div className="panel-body">
            {isLoading ? (
              <div className="skel" style={{ width: '100%', height: 200 }} />
            ) : (
              <>
                <p className="acta-sub">{err?.status === 404 ? 'El acta no existe.' : err?.detail}</p>
                <button className="btn-secondary" onClick={err?.status === 404 ? () => navigate('/actas') : refetch}>
                  {err?.status === 404 ? 'Volver a actas' : 'Reintentar'}
                </button>
              </>
            )}
          </div>
        </div>
      </AppShell>
    );
  }

  const annulled = acta.status === 'ANULADA';
  const doAnnul = async () => {
    if (reason.trim().length < 5) {
      showToast('Indicá el motivo de la anulación (mínimo 5 caracteres).');
      return;
    }
    try {
      await annul({ id: acta.id, reason: reason.trim() }).unwrap();
      setAnnulOpen(false);
      setReason('');
      showToast('Acta anulada correctamente.');
    } catch (err) {
      showToast(toApiError(err).detail);
    }
  };
  const doSync = async () => {
    try {
      await sync(acta.id).unwrap();
      showToast('Sincronización con Gestión Académica reintentada.');
    } catch (err) {
      showToast(toApiError(err).detail);
    }
  };
  const pdf = async () => {
    showToast('Generando PDF...');
    try {
      const { downloadActaPdf } = await import('../lib/actaPdf'); // jsPDF se carga solo cuando hace falta
      downloadActaPdf(acta);
      showToast('PDF generado correctamente.');
    } catch {
      showToast('No pudimos generar el PDF.');
    }
  };

  return (
    <AppShell
      scope="17"
      active="actas"
      after={
        <>
          <div className={`toast${toast.show ? ' show' : ''}`}>
            <I.i47 />
            <span>{toast.message}</span>
          </div>
          <div className={`sheet-overlay${overlay ? ' show' : ''}`}>
            <button className="close-overlay" aria-label="Cerrar vista ampliada" onClick={() => setOverlay(false)}>
              <I.i76 />
            </button>
            <div>{overlay && <Sheet acta={acta} />}</div>
          </div>
        </>
      }
    >
      {crumbs(`${NAME[acta.type]} N.º ${acta.number}`)}
      <div className="acta-header-top">
        <div className="acta-title-block">
          <div className="acta-title-row">
            <h1>{NAME[acta.type]}</h1>
            {annulled && (
              <span className="badge-status" style={{ background: 'var(--error-100)', color: 'var(--error-600)' }}>
                Anulada
              </span>
            )}
          </div>
          <p className="acta-number">N.º {acta.number}</p>
          <p className="acta-sub">
            {acta.subject} · Comisión {acta.commission}
          </p>
        </div>
        <div className="acta-actions">
          <button className="btn-secondary" onClick={() => navigate('/actas')}>
            <I.i86 />
            Volver a actas
          </button>
        </div>
      </div>
      <div className="acta-layout">
        <div className="acta-sheet-wrap">
          <Sheet acta={acta} />
          <button className="btn-secondary sheet-expand-btn" onClick={() => setOverlay(true)}>
            <I.i88 />
            Ampliar documento
          </button>
        </div>
        <div className="info-col">
          <div className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Información del acta</h2>
            </div>
            <div className="panel-body">
              <div className="info-grid">
                <div className="info-item">
                  <span className="k">Número</span>
                  <span className="v">{acta.number}</span>
                </div>
                <div className="info-item">
                  <span className="k">Tipo</span>
                  <span className="v">{acta.type === 'FINAL' ? 'Acta final' : 'Acta de cursada'}</span>
                </div>
                <div className="info-item full">
                  <span className="k">Curso</span>
                  <span className="v">{acta.subject}</span>
                </div>
                <div className="info-item">
                  <span className="k">Comisión</span>
                  <span className="v">{acta.commission}</span>
                </div>
                <div className="info-item">
                  <span className="k">Período</span>
                  <span className="v">{acta.period}</span>
                </div>
                <div className="info-item">
                  <span className="k">Fecha</span>
                  <span className="v">{shortDate(acta.date)}</span>
                </div>
                <div className="info-item">
                  <span className="k">Sincronización</span>
                  <span className="v">
                    {acta.sync.ok} ok · {acta.sync.error} con error
                  </span>
                </div>
                <div className="info-item full">
                  <span className="k">Docente responsable</span>
                  <span className="v">{acta.teacherName}</span>
                </div>
                {annulled && (
                  <div className="info-item full">
                    <span className="k">Motivo de anulación</span>
                    <span className="v">{acta.annulmentReason}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
          <div className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Acciones</h2>
            </div>
            <div className="panel-actions">
              <button className="btn-secondary" onClick={pdf}>
                <I.i89 />
                Descargar PDF
              </button>
              <button className="btn-secondary" onClick={() => window.print()}>
                <I.i90 />
                Imprimir
              </button>
              {!annulled && acta.sync.error > 0 && (
                <button className="btn-secondary" disabled={syncState.isLoading} onClick={doSync}>
                  <I.i45 />
                  {syncState.isLoading ? 'Sincronizando…' : 'Reintentar sincronización'}
                </button>
              )}
              {!annulled && !annulOpen && (
                <button className="btn-secondary" style={{ color: 'var(--error-600)' }} onClick={() => setAnnulOpen(true)}>
                  <I.i76 />
                  Anular acta
                </button>
              )}
              {annulOpen && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%' }}>
                  <label className="k" htmlFor="annulReason" style={{ fontSize: 12.5, fontWeight: 600 }}>
                    Motivo de la anulación
                  </label>
                  <textarea
                    id="annulReason"
                    rows={3}
                    value={reason}
                    maxLength={500}
                    onChange={(e) => setReason(e.target.value)}
                    style={{ font: 'inherit', fontSize: 13, padding: 10, borderRadius: 8, border: '1px solid var(--border)', resize: 'vertical' }}
                  />
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn-secondary" onClick={() => setAnnulOpen(false)}>
                      Volver
                    </button>
                    <button
                      className="btn-secondary"
                      style={{ color: '#fff', background: 'var(--error-600)', borderColor: 'var(--error-600)' }}
                      disabled={annulState.isLoading}
                      onClick={doAnnul}
                    >
                      {annulState.isLoading ? 'Anulando…' : 'Confirmar anulación'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
