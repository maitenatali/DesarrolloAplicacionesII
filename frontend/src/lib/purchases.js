// Compras de la Tienda del Campus (GET /purchases, shape del evento store.purchase.completed.v1).
export const purchaseCode = (p) => `#${p.purchaseId.slice(0, 8).toUpperCase()}`;

export function purchaseName(p) {
  const first = p.items?.[0]?.productName || 'Compra';
  return p.items?.length > 1 ? `${first} y ${p.items.length - 1} más` : first;
}
