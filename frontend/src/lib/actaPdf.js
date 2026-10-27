// PDF del acta generado en el navegador (el backend no genera PDFs; ver diseño §1 "Non-goals").
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import { grade, isoShortDate, isoTime, longDate } from './format';
import { RESULT_LABEL } from './domain';

const NAVY = [27, 42, 74];

export function downloadActaPdf(acta) {
  const doc = new jsPDF({ unit: 'pt', format: 'a4' });
  const w = doc.internal.pageSize.getWidth();
  const title = acta.type === 'FINAL' ? 'ACTA FINAL' : 'ACTA DE CURSADA';

  doc.setFont('helvetica', 'bold').setFontSize(16).setTextColor(...NAVY).text('UADE', w / 2, 56, { align: 'center' });
  doc.setFont('helvetica', 'normal').setFontSize(9).setTextColor(100).text('Universidad Argentina de la Empresa', w / 2, 70, { align: 'center' });
  doc.setFontSize(9).text('ACTA ACADÉMICA', w / 2, 100, { align: 'center' });
  doc.setFont('helvetica', 'bold').setFontSize(18).setTextColor(...NAVY).text(title, w / 2, 122, { align: 'center' });
  doc.setFont('helvetica', 'normal').setFontSize(10).setTextColor(80).text(`N.º ${acta.number}`, w / 2, 138, { align: 'center' });
  if (acta.status === 'ANULADA') {
    doc.setTextColor(179, 57, 44).setFont('helvetica', 'bold').text('ANULADA', w / 2, 154, { align: 'center' });
  }

  const data = [
    ['Curso', acta.subject],
    ['Comisión', acta.commission],
    ['Período', acta.period],
    ['Fecha', longDate(acta.date)],
    ['Docente', acta.teacherName],
  ];
  autoTable(doc, {
    startY: 170,
    body: data,
    theme: 'plain',
    styles: { fontSize: 10, cellPadding: 3 },
    columnStyles: { 0: { fontStyle: 'bold', cellWidth: 90, textColor: 90 } },
  });

  autoTable(doc, {
    startY: doc.lastAutoTable.finalY + 18,
    head: [['N.º', 'Estudiante', 'Legajo', 'Resultado', 'Condición']],
    body: (acta.rows || []).map((r) => [r.order, r.studentName, r.studentFileNumber, grade(r.grade), RESULT_LABEL[r.result] || r.result]),
    headStyles: { fillColor: NAVY, fontSize: 9 },
    styles: { fontSize: 9 },
  });

  let y = doc.lastAutoTable.finalY + 22;
  const c = acta.counts || {};
  const summary =
    acta.type === 'FINAL'
      ? `${c.approved || 0} aprobados · ${c.failed || 0} desaprobados · ${c.absent || 0} ausentes`
      : `${c.regular || 0} regulares · ${c.free || 0} libres`;
  doc.setFont('helvetica', 'bold').setFontSize(10).setTextColor(30).text(`Total de estudiantes: ${(acta.rows || []).length}`, 40, y);
  doc.setFont('helvetica', 'normal').text(summary, 40, (y += 14));
  if (acta.notes) {
    doc.setFont('helvetica', 'bold').text('Observaciones', 40, (y += 24));
    doc.setFont('helvetica', 'normal').text(doc.splitTextToSize(acta.notes, w - 80), 40, (y += 14));
  }
  y += 70;
  doc.setDrawColor(150).line(w / 2 - 100, y, w / 2 + 100, y);
  doc.setFont('helvetica', 'bold').text(acta.teacherName || '', w / 2, (y += 14), { align: 'center' });
  doc.setFont('helvetica', 'normal').setFontSize(9).text('Docente responsable', w / 2, (y += 12), { align: 'center' });
  doc.text(`${isoShortDate(acta.generatedAt)} · ${isoTime(acta.generatedAt)}`, w / 2, (y += 12), { align: 'center' });

  doc.save(`acta-${acta.number}.pdf`);
}
