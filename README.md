# 🔤 Font to SVG Web Converter

Uma ferramenta web simples para converter fontes TTF/OTF em visualizações SVG dos glifos.

## 🚀 Como usar

### Instalação

1. Clone o repositório:
```bash
git clone <repo-url>
cd teste
```

2. Instale as dependências:
```bash
npm install
```

3. Inicie o servidor:
```bash
npm start
```

4. Abra seu navegador e acesse:
```
http://localhost:3000
```

### Usando a aplicação

1. **Selecione uma fonte**: Clique na área de upload ou arraste um arquivo `.ttf` ou `.otf`
2. **Digite os caracteres**: Escreva os caracteres que deseja visualizar (ex: ABC123)
3. **Visualize o SVG**: Os glifos serão renderizados como caminhos SVG
4. **Baixe o resultado**: Clique em "Baixar SVG" para exportar os glifos

## 🎨 Funcionalidades

- ✅ Upload de fontes TTF e OTF
- ✅ Parsing automático da fonte
- ✅ Extração de glifos como caminhos SVG
- ✅ Seleção personalizável de caracteres
- ✅ Visualização em tempo real
- ✅ Exportação de SVG para download
- ✅ Interface responsiva
- ✅ Drag & drop de arquivos
- ✅ Tratamento de erros

## 🛠️ Estrutura do projeto

```
├── index.html       # Interface HTML
├── style.css        # Estilos CSS
├── app.js           # Lógica JavaScript do cliente
├── server.js        # Servidor Express
├── package.json     # Dependências
└── README.md        # Este arquivo
```

## 📱 Requisitos

- Node.js 12+
- Navegador moderno com suporte a SVG (Chrome, Firefox, Safari, Edge)

## 🔧 Desenvolvido com

- **Frontend**: HTML5, CSS3, JavaScript vanilla
- **Backend**: Node.js + Express
- **Parsing de Fontes**: opentype.js
- **Visualização**: SVG nativo
- **Estilo**: Gradientes modernos e design responsivo

## 💡 Exemplos de uso

### Exportar um alfabeto completo
Digite no campo: `ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz`

### Exportar números
Digite no campo: `0123456789`

### Exportar símbolos específicos
Digite no campo: `@#$%&*!?`

## 📄 Licença

MIT
