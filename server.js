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

if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir);
}

if (!fs.existsSync(outputsDir)) {
  fs.mkdirSync(outputsDir);
}

const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, uploadsDir);
  },
  filename: function (req, file, cb) {
    const uniqueName = `${Date.now()}-${file.originalname}`;
    cb(null, uniqueName);
  }
});

const upload = multer({
  storage,
  fileFilter: function (req, file, cb) {
    if (file.mimetype !== 'application/pdf') {
      return cb(new Error('Solo se permiten archivos PDF'));
    }

    cb(null, true);
  }
});

app.get('/', (req, res) => {
  res.json({
    message: 'API lector de facturas funcionando'
  });
});

app.post('/procesar-factura', upload.single('factura'), (req, res) => {
  if (!req.file) {
    return res.status(400).json({
      error: 'No se subió ninguna factura'
    });
  }

  const pdfPath = req.file.path;
  const outputFileName = `${path.parse(req.file.filename).name}.xlsx`;
  const outputPath = path.join(outputsDir, outputFileName);

  const pythonExecutable = path.join(__dirname, '.venv', 'Scripts', 'python.exe');
  const scriptPath = path.join(__dirname, 'scripts', 'extraer_factura.py');

  const pythonProcess = spawn(pythonExecutable, [
    scriptPath,
    pdfPath,
    outputPath
  ]);

  let stdout = '';
  let stderr = '';

  pythonProcess.stdout.on('data', (data) => {
    stdout += data.toString();
  });

  pythonProcess.stderr.on('data', (data) => {
    stderr += data.toString();
  });

  pythonProcess.on('close', (code) => {
    if (code !== 0) {
      console.error(stderr);

      return res.status(500).json({
        error: 'Error procesando la factura',
        detalle: stderr
      });
    }

    return res.download(outputPath, 'factura_procesada.xlsx');
  });
});

const PORT = 3000;

app.listen(PORT, () => {
  console.log(`Servidor iniciado en http://localhost:${PORT}`);
});