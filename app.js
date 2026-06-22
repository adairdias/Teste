// Global variables
let currentInkContent = '';
let currentFileName = '';

// DOM elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const controls = document.getElementById('controls');
const previewSection = document.getElementById('previewSection');
const svgContainer = document.getElementById('svgContainer');
const errorDiv = document.getElementById('error');
const spinner = document.getElementById('loadingSpinner');
const downloadBtn = document.getElementById('downloadBtn');
const resetBtn = document.getElementById('resetBtn');

// Setup file input
fileInput.addEventListener('change', handleFileSelect);

// Setup drag and drop
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

// Setup button events
downloadBtn.addEventListener('click', downloadSVG);
resetBtn.addEventListener('click', reset);

function handleFileSelect() {
    const file = fileInput.files[0];
    if (!file) return;

    if (!file.name.endsWith('.ink')) {
        showError('Por favor, selecione um arquivo .ink válido');
        return;
    }

    currentFileName = file.name.replace('.ink', '');
    const reader = new FileReader();

    reader.onload = (e) => {
        try {
            showSpinner(true);
            clearError();
            currentInkContent = e.target.result;
            processInkFile(currentInkContent);
        } catch (error) {
            showError('Erro ao processar arquivo: ' + error.message);
            showSpinner(false);
        }
    };

    reader.onerror = () => {
        showError('Erro ao ler arquivo');
        showSpinner(false);
    };

    reader.readAsText(file);
}

function processInkFile(inkContent) {
    try {
        // Parse a estrutura do arquivo ink
        const storyStructure = parseInkStructure(inkContent);

        // Gera o SVG
        const svg = generateStoryVisualization(storyStructure);

        // Exibe o resultado
        svgContainer.innerHTML = '';
        svgContainer.appendChild(svg);

        previewSection.style.display = 'block';
        controls.style.display = 'flex';
        uploadArea.style.opacity = '0.5';
        uploadArea.style.pointerEvents = 'none';

        showSpinner(false);
    } catch (error) {
        showError('Erro ao processar arquivo Ink: ' + error.message);
        showSpinner(false);
    }
}

function parseInkStructure(content) {
    const lines = content.split('\n');
    const nodes = [];
    const connections = [];
    let currentDepth = 0;
    const nodeStack = [];

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        if (!line || line.startsWith('//')) continue;

        const depth = getIndentation(lines[i]);

        // Detecta nós (linhas que começam com =)
        if (line.startsWith('=')) {
            const nodeLabel = line.substring(1).trim() || `Node ${nodes.length}`;
            const nodeId = nodes.length;
            nodes.push({ id: nodeId, label: nodeLabel, depth: depth });

            if (nodeStack.length > 0 && depth > currentDepth) {
                connections.push({
                    from: nodeStack[nodeStack.length - 1],
                    to: nodeId
                });
            }
            nodeStack.push(nodeId);
            currentDepth = depth;
        }
        // Detecta escolhas (linhas que começam com *)
        else if (line.startsWith('*')) {
            const choiceLabel = line.substring(1).trim() || 'Escolha';
            const nodeId = nodes.length;
            nodes.push({ id: nodeId, label: choiceLabel, depth: depth, isChoice: true });

            if (nodeStack.length > 0) {
                connections.push({
                    from: nodeStack[nodeStack.length - 1],
                    to: nodeId
                });
            }
            nodeStack.push(nodeId);
        }
        // Detecta diálogos e texto
        else if (line && !line.startsWith('{') && !line.startsWith('[')) {
            if (nodes.length === 0) {
                nodes.push({ id: 0, label: 'Início', depth: 0 });
            }

            const lastNode = nodes[nodes.length - 1];
            if (lastNode.label.length < 100) {
                lastNode.label += '\n' + line.substring(0, 50);
            }
        }
    }

    return { nodes, connections };
}

function getIndentation(line) {
    const match = line.match(/^(\s*)/);
    return match ? match[1].length : 0;
}

function generateStoryVisualization(structure) {
    const { nodes, connections } = structure;

    if (nodes.length === 0) {
        nodes.push({ id: 0, label: 'Arquivo vazio', depth: 0 });
    }

    const nodeRadius = 40;
    const horizontalSpacing = 200;
    const verticalSpacing = 150;
    const padding = 50;

    // Calcula posições dos nós em árvore
    const positions = new Map();
    const depthCounts = new Map();

    nodes.forEach(node => {
        const depth = node.depth || 0;
        const count = depthCounts.get(depth) || 0;
        depthCounts.set(depth, count + 1);

        const x = padding + depth * horizontalSpacing;
        const y = padding + count * verticalSpacing;
        positions.set(node.id, { x, y });
    });

    const maxDepth = Math.max(...nodes.map(n => n.depth || 0));
    const maxWidth = (maxDepth + 1) * horizontalSpacing + 2 * padding;
    const maxHeight = nodes.length * verticalSpacing + 2 * padding;

    // Cria SVG
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', maxWidth);
    svg.setAttribute('height', maxHeight);
    svg.setAttribute('viewBox', `0 0 ${maxWidth} ${maxHeight}`);
    svg.style.backgroundColor = '#fff';

    // Desenha conexões primeiro (para aparecer atrás dos nós)
    connections.forEach(conn => {
        const fromPos = positions.get(conn.from);
        const toPos = positions.get(conn.to);

        if (fromPos && toPos) {
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', fromPos.x);
            line.setAttribute('y1', fromPos.y);
            line.setAttribute('x2', toPos.x);
            line.setAttribute('y2', toPos.y);
            line.setAttribute('stroke', '#bbb');
            line.setAttribute('stroke-width', '2');
            svg.appendChild(line);

            // Desenha seta
            drawArrow(svg, fromPos.x, fromPos.y, toPos.x, toPos.y);
        }
    });

    // Desenha nós
    nodes.forEach(node => {
        const pos = positions.get(node.id);
        if (!pos) return;

        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');

        // Círculo ou retângulo para o nó
        if (node.isChoice) {
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', pos.x - nodeRadius);
            rect.setAttribute('y', pos.y - 25);
            rect.setAttribute('width', nodeRadius * 2);
            rect.setAttribute('height', 50);
            rect.setAttribute('fill', '#ff9800');
            rect.setAttribute('stroke', '#f57c00');
            rect.setAttribute('stroke-width', '2');
            rect.setAttribute('rx', '5');
            g.appendChild(rect);
        } else {
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('cx', pos.x);
            circle.setAttribute('cy', pos.y);
            circle.setAttribute('r', nodeRadius);
            circle.setAttribute('fill', '#667eea');
            circle.setAttribute('stroke', '#764ba2');
            circle.setAttribute('stroke-width', '2');
            g.appendChild(circle);
        }

        // Texto do nó
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', pos.x);
        text.setAttribute('y', pos.y);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('dy', '0.3em');
        text.setAttribute('fill', 'white');
        text.setAttribute('font-size', '12');
        text.setAttribute('font-weight', 'bold');
        text.setAttribute('pointer-events', 'none');

        const label = node.label.substring(0, 15) + (node.label.length > 15 ? '...' : '');
        text.textContent = label;
        g.appendChild(text);

        // Tooltip
        const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
        title.textContent = node.label;
        g.appendChild(title);

        svg.appendChild(g);
    });

    return svg;
}

function drawArrow(svg, fromX, fromY, toX, toY) {
    const headlen = 15;
    const angle = Math.atan2(toY - fromY, toX - fromX);

    const arrowX = toX - headlen * Math.cos(angle);
    const arrowY = toY - headlen * Math.sin(angle);

    const points = [
        toX + ',\n' + toY,
        (arrowX - 10 * Math.cos(angle - Math.PI / 6)) + ',' + (arrowY - 10 * Math.sin(angle - Math.PI / 6)),
        (arrowX - 10 * Math.cos(angle + Math.PI / 6)) + ',' + (arrowY - 10 * Math.sin(angle + Math.PI / 6))
    ].join(' ');

    const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    polygon.setAttribute('points', points);
    polygon.setAttribute('fill', '#bbb');
    svg.appendChild(polygon);
}

function downloadSVG() {
    if (!svgContainer.innerHTML) return;

    const svg = svgContainer.querySelector('svg');
    const svgData = new XMLSerializer().serializeToString(svg);
    const blob = new Blob([svgData], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `${currentFileName || 'story'}.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

function reset() {
    fileInput.value = '';
    currentInkContent = '';
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
