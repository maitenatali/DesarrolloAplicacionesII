import * as I from './icons.generated';

/** Controles de paginación de los mockups. `iconArrows` usa los chevrons SVG; si no, ‹ ›. */
export function paginate(items, page, size) {
  const total = items.length;
  const pages = Math.max(1, Math.ceil(total / size));
  const current = Math.min(Math.max(1, page), pages);
  const start = total ? (current - 1) * size + 1 : 0;
  const end = Math.min(current * size, total);
  return { pages, current, start, end, total, items: items.slice((current - 1) * size, current * size) };
}

export default function Pagination({ pager, onChange, iconArrows = false }) {
  const { current, pages } = pager;
  return (
    <div className="pagination-controls">
      <button className="page-btn" disabled={current === 1} aria-label="Página anterior" onClick={() => onChange(current - 1)}>
        {iconArrows ? <I.i33 /> : '‹'}
      </button>
      {Array.from({ length: pages }, (_, i) => (
        <button key={i} className={`page-btn${i + 1 === current ? ' active' : ''}`} onClick={() => onChange(i + 1)}>
          {i + 1}
        </button>
      ))}
      <button className="page-btn" disabled={current === pages} aria-label="Página siguiente" onClick={() => onChange(current + 1)}>
        {iconArrows ? <I.i34 /> : '›'}
      </button>
    </div>
  );
}
