const invoiceForm = document.querySelector('#invoice-form');
const invoiceFile = document.querySelector('#invoice-file');
const invoiceStatus = document.querySelector('#invoice-status');
const providerForm = document.querySelector('#provider-form');
const providerStatus = document.querySelector('#provider-status');
const providersTable = document.querySelector('#providers-table');
const mappingForm = document.querySelector('#mapping-form');
const mappingStatus = document.querySelector('#mapping-status');
const mappingsTable = document.querySelector('#mappings-table');
const mappingProvider = document.querySelector('#mapping-provider');

let providers = [];

function setStatus(element, message, type = '') {
  element.textContent = message;
  element.className = `status-text ${type}`.trim();
}

function addCell(row, value, className = '') {
  const cell = document.createElement('td');
  cell.textContent = value || '';

  if (className) {
    cell.className = className;
  }

  row.appendChild(cell);
}

function renderProviders(items) {
  providersTable.replaceChildren();
  mappingProvider.replaceChildren();

  if (!items.length) {
    const row = document.createElement('tr');
    addCell(row, 'Sin proveedores cargados', 'empty-row');
    addCell(row, '');
    addCell(row, '');
    providersTable.appendChild(row);
  }

  for (const provider of items) {
    const row = document.createElement('tr');
    addCell(row, provider.id);
    addCell(row, provider.name);
    addCell(row, provider.cuit);
    providersTable.appendChild(row);

    const option = document.createElement('option');
    option.value = provider.id;
    option.textContent = provider.name;
    mappingProvider.appendChild(option);
  }

  mappingForm.querySelector('button').disabled = items.length === 0;
}

function renderMappings(items) {
  mappingsTable.replaceChildren();

  if (!items.length) {
    const row = document.createElement('tr');
    addCell(row, 'Sin mapeos cargados', 'empty-row');
    addCell(row, '');
    addCell(row, '');
    addCell(row, '');
    mappingsTable.appendChild(row);
    return;
  }

  for (const mapping of items) {
    const row = document.createElement('tr');
    addCell(row, mapping.provider_name);
    addCell(row, mapping.provider_product_code);
    addCell(row, mapping.provider_product_description);
    addCell(row, mapping.internal_product_code);
    mappingsTable.appendChild(row);
  }
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.error || 'Error inesperado');
  }

  return payload;
}

async function loadProviders() {
  providers = await fetchJson('/api/providers');
  renderProviders(providers);
}

async function loadMappings() {
  const mappings = await fetchJson('/api/product-mappings');
  renderMappings(mappings);
}

function getDownloadName(response) {
  const disposition = response.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="?([^"]+)"?/i);

  return match ? match[1] : 'factura_procesada.xls';
}

invoiceForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  if (!invoiceFile.files.length) {
    setStatus(invoiceStatus, 'No se selecciono PDF', 'error');
    return;
  }

  const submitButton = invoiceForm.querySelector('button');
  const formData = new FormData();
  formData.append('factura', invoiceFile.files[0]);

  try {
    submitButton.disabled = true;
    setStatus(invoiceStatus, 'Procesando factura...');

    const response = await fetch('/procesar-factura', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detalle || payload.error || 'Error procesando la factura');
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = getDownloadName(response);
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);

    setStatus(invoiceStatus, 'Factura procesada correctamente', 'ok');
  } catch (error) {
    console.error(error);
    setStatus(invoiceStatus, 'Error procesando la factura', 'error');
  } finally {
    submitButton.disabled = false;
  }
});

providerForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const submitButton = providerForm.querySelector('button');
  const formData = new FormData(providerForm);

  try {
    submitButton.disabled = true;
    setStatus(providerStatus, 'Guardando...');

    await fetchJson('/api/providers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: formData.get('name'),
        cuit: formData.get('cuit')
      })
    });

    providerForm.reset();
    await loadProviders();
    setStatus(providerStatus, 'Proveedor guardado', 'ok');
  } catch (error) {
    console.error(error);
    setStatus(providerStatus, 'Error guardando proveedor', 'error');
  } finally {
    submitButton.disabled = false;
  }
});

mappingForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const submitButton = mappingForm.querySelector('button');
  const formData = new FormData(mappingForm);

  try {
    submitButton.disabled = true;
    setStatus(mappingStatus, 'Guardando...');

    await fetchJson('/api/product-mappings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider_id: Number(formData.get('provider_id')),
        provider_product_code: formData.get('provider_product_code'),
        provider_product_description: formData.get('provider_product_description'),
        internal_product_code: formData.get('internal_product_code')
      })
    });

    mappingForm.reset();
    await loadMappings();
    setStatus(mappingStatus, 'Mapeo guardado', 'ok');
  } catch (error) {
    console.error(error);
    setStatus(mappingStatus, 'Error guardando mapeo', 'error');
  } finally {
    submitButton.disabled = false;
  }
});

async function init() {
  try {
    await loadProviders();
    await loadMappings();
  } catch (error) {
    console.error(error);
    setStatus(providerStatus, 'Error consultando la base de datos', 'error');
  }
}

init();
