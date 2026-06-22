let currentFont = null;
let currentFileName = '';

const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const controls = document.getElementById('controls');
const previewSection = document.getElementById('previewSection');
const svgContainer = document.getElementById('svgContainer');
const errorDiv = document.getElementById('error');
const spinner = document.getElementById('loadingSpinner');
const downloadBtn = document.getElementById('downloadBtn');
const resetBtn = document.getElementById('resetBtn');
const updateBtn = document.getElementById('updateBtn');
const charInput = document.getElementById('charInput');

fileInput.addEventListener('change', handleFileSelect);

uploadArea.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
});
uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('drag-over');
});
uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        fileInput.files = files;
        handleFileSelect();
    }
});

downloadBtn.addEventListener('click', downloadSVG);
resetBtn.addEventListener('click', reset);
updateBtn.addEventListener('click', updatePreview);

function handleFileSelect() {
    const file = fileInput.files[0];
    if (!file) return;

    const validExtensions = ['.ttf', '.otf'];
    const hasValidExtension = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));

    if (!hasValidExtension) {
        showError('Por favor, selecione um arquivo .ttf ou .otf válido');
        return;
    }

    currentFileName = file.name.split('.').slice(0, -1).join('.');
    const reader = new FileReader();

    reader.onload = (e) => {
        try {
            showSpinner(true);
            clearError();
            processFont(e.target.result);
        } catch (error) {
            showError('Erro ao processar fonte: ' + error.message);
            showSpinner(false);
        }
    };

    reader.onerror = () => {
        showError('Erro ao ler arquivo');
        showSpinner(false);
    };

    reader.readAsArrayBuffer(file);
}

function processFont(fontData) {
    try {
        currentFont = opentype.parse(fontData);

        if (!currentFont) {
            showError('Não foi possível fazer parse da fonte');
            showSpinner(false);
            return;
        }

        updatePreview();
    } catch (error) {
        showError('Erro ao fazer parse da fonte: ' + error.message);
        showSpinner(false);
    }
}

function updatePreview() {
    if (!currentFont) return;

    try {
        const chars = charInput.value || 'A';
        const svg = generateFontVisualization(currentFont, chars);

        svgContainer.innerHTML = '';
        svgContainer.appendChild(svg);

        previewSection.style.display = 'block';
        controls.style.display = 'block';
        uploadArea.style.opacity = '0.5';
        uploadArea.style.pointerEvents = 'none';

        showSpinner(false);
    } catch (error) {
        showError('Erro ao gerar visualização: ' + error.message);
        showSpinner(false);
    }
}

function generateFontVisualization(font, characters) {
    const fontSize = 120;
    const padding = 50;
    const charSpacing = fontSize + 40;
    let totalWidth = padding * 2;
    let maxHeight = fontSize + padding * 2;

    totalWidth += characters.length * charSpacing;

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', totalWidth);
    svg.setAttribute('height', maxHeight);
    svg.setAttribute('viewBox', `0 0 ${totalWidth} ${maxHeight}`);
    svg.style.backgroundColor = '#fff';

    let xOffset = padding;

    for (const char of characters) {
        const glyph = font.charToGlyph(char);

        if (!glyph || glyph.advanceWidth === 0) continue;

        const path = glyph.getPath(xOffset, padding + fontSize, fontSize);

        const pathElement = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        pathElement.setAttribute('d', path.toPathData(2));
        pathElement.setAttribute('fill', '#667eea');
        pathElement.setAttribute('stroke', '#764ba2');
        pathElement.setAttribute('stroke-width', '0.5');
        pathElement.style.pointerEvents = 'none';

        svg.appendChild(pathElement);

        xOffset += charSpacing;
    }

    return svg;
}

function downloadSVG() {
    if (!svgContainer.innerHTML) return;

    const svg = svgContainer.querySelector('svg');
    const svgData = new XMLSerializer().serializeToString(svg);
    const blob = new Blob([svgData], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `${currentFileName || 'font'}.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

function reset() {
    fileInput.value = '';
    charInput.value = 'ABC';
    currentFont = null;
    currentFileName = '';
    svgContainer.innerHTML = '';
    previewSection.style.display = 'none';
    controls.style.display = 'none';
    uploadArea.style.opacity = '1';
    uploadArea.style.pointerEvents = 'auto';
    clearError();
}

function showError(message) {
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

function clearError() {
    errorDiv.style.display = 'none';
    errorDiv.textContent = '';
}

function showSpinner(show) {
    spinner.style.display = show ? 'block' : 'none';
}
