const express = require('express');
const multer = require('multer');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const app = express();

app.use(cors());
app.use(express.json());

const uploadsDir = path.join(__dirname, 'uploads');
const outputsDir = path.join(__dirname, 'outputs');
const databaseDir = path.join(__dirname, 'database');
const publicDir = path.join(__dirname, 'public');
const dbPath = path.join(databaseDir, 'facturas.sqlite');
const pythonExecutable = path.join(__dirname, '.venv', 'Scripts', 'python.exe');

function ensureDirectory(directoryPath) {
  if (!fs.existsSync(directoryPath)) {
    fs.mkdirSync(directoryPath, { recursive: true });
  }
}

ensureDirectory(uploadsDir);
ensureDirectory(outputsDir);
ensureDirectory(databaseDir);

app.use(express.static(publicDir));

const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, uploadsDir);
  },
  filename: function (req, file, cb) {
    const safeOriginalName = path.basename(file.originalname);
    const uniqueName = `${Date.now()}-${safeOriginalName}`;
    cb(null, uniqueName);
  }
});

const upload = multer({
  storage,
  fileFilter: function (req, file, cb) {
    const extension = path.extname(file.originalname).toLowerCase();

    if (file.mimetype !== 'application/pdf' && extension !== '.pdf') {
      return cb(new Error('Solo se permiten archivos PDF'));
    }

    cb(null, true);
  }
});

function runPython(scriptPath, args, input) {
  return new Promise((resolve, reject) => {
    const pythonProcess = spawn(pythonExecutable, [scriptPath, ...args], {
      env: {
        ...process.env,
        PYTHONIOENCODING: 'utf-8'
      }
    });

    let stdout = '';
    let stderr = '';

    pythonProcess.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    pythonProcess.on('error', (error) => {
      reject(error);
    });

    pythonProcess.on('close', (code) => {
      if (code !== 0) {
        const error = new Error(stderr || `Python finalizo con codigo ${code}`);
        error.stderr = stderr;
        error.stdout = stdout;
        return reject(error);
      }

      resolve({ stdout, stderr });
    });

    if (input) {
      pythonProcess.stdin.write(input);
    }

    pythonProcess.stdin.end();
  });
}

async function runDbCommand(action, payload = {}) {
  const scriptPath = path.join(__dirname, 'scripts', 'db_cli.py');
  const { stdout } = await runPython(
    scriptPath,
    [action, dbPath],
    JSON.stringify(payload)
  );

  const parsed = JSON.parse(stdout);

  if (!parsed.ok) {
    throw new Error(parsed.error || 'Error de base de datos');
  }

  return parsed.data;
}

function getPythonErrorMessage(error) {
  if (error.stderr) {
    try {
      const parsed = JSON.parse(error.stderr);
      return parsed.error || error.stderr;
    } catch (_parseError) {
      return error.stderr;
    }
  }

  return error.message;
}

app.get('/api/providers', async (req, res) => {
  try {
    const providers = await runDbCommand('list_providers');
    res.json(providers);
  } catch (error) {
    console.error('Error de base de datos:', getPythonErrorMessage(error));
    res.status(500).json({ error: 'Error consultando proveedores' });
  }
});

app.post('/api/providers', async (req, res) => {
  try {
    const { name, cuit } = req.body;

    if (!name || !String(name).trim()) {
      return res.status(400).json({ error: 'El nombre del proveedor es obligatorio' });
    }

    const provider = await runDbCommand('create_provider', { name, cuit });
    res.status(201).json(provider);
  } catch (error) {
    console.error('Error de base de datos:', getPythonErrorMessage(error));
    res.status(500).json({ error: 'Error guardando proveedor' });
  }
});

app.get('/api/product-mappings', async (req, res) => {
  try {
    const mappings = await runDbCommand('list_product_mappings');
    res.json(mappings);
  } catch (error) {
    console.error('Error de base de datos:', getPythonErrorMessage(error));
    res.status(500).json({ error: 'Error consultando mapeos de productos' });
  }
});

app.post('/api/product-mappings', async (req, res) => {
  try {
    const {
      provider_id,
      provider_product_code,
      provider_product_description,
      internal_product_code
    } = req.body;

    if (!provider_id) {
      return res.status(400).json({ error: 'El proveedor es obligatorio' });
    }

    if (!provider_product_code || !String(provider_product_code).trim()) {
      return res.status(400).json({
        error: 'El codigo de producto del proveedor es obligatorio'
      });
    }

    if (!internal_product_code || !String(internal_product_code).trim()) {
      return res.status(400).json({ error: 'El codigo interno es obligatorio' });
    }

    const mapping = await runDbCommand('create_product_mapping', {
      provider_id,
      provider_product_code,
      provider_product_description,
      internal_product_code
    });

    res.status(201).json(mapping);
  } catch (error) {
    console.error('Error de base de datos:', getPythonErrorMessage(error));
    res.status(500).json({ error: 'Error guardando mapeo de producto' });
  }
});

app.post('/procesar-factura', upload.single('factura'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({
      error: 'No se subio ninguna factura PDF'
    });
  }

  const pdfPath = req.file.path;
  const outputFileName = `${path.parse(req.file.filename).name}.xls`;
  const outputPath = path.join(outputsDir, outputFileName);
  const scriptPath = path.join(__dirname, 'scripts', 'extraer_factura.py');

  try {
    await runPython(scriptPath, [pdfPath, outputPath, dbPath]);

    return res.download(outputPath, 'factura_procesada.xls');
  } catch (error) {
    const detail = getPythonErrorMessage(error);
    console.error('Error ejecutando Python:', detail);

    return res.status(500).json({
      error: 'Error procesando la factura',
      detalle: detail
    });
  }
});

app.use((error, req, res, next) => {
  if (error instanceof multer.MulterError || error.message === 'Solo se permiten archivos PDF') {
    return res.status(400).json({ error: error.message });
  }

  next(error);
});

const PORT = 3000;

app.listen(PORT, () => {
  console.log(`Servidor iniciado en http://localhost:${PORT}`);
});
