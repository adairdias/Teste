# 📖 Ink to SVG Web Converter

Uma ferramenta web simples para converter arquivos Ink em visualizações SVG do fluxo narrativo.

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

1. **Selecione um arquivo Ink**: Clique na área de upload ou arraste um arquivo `.ink`
2. **Visualize o SVG**: A estrutura do seu arquivo Ink será visualizada como um diagrama SVG
3. **Baixe o resultado**: Clique em "Baixar SVG" para exportar a visualização

## 📝 Formato Ink suportado

A aplicação reconhece:
- Nós (linhas começando com `=`): Representam pontos principais da história
- Escolhas (linhas começando com `*`): Representam decisões do leitor
- Diálogos e texto: Texto livre é incluído nos nós
- Indentação: Representa a profundidade/hierarquia da história

### Exemplo de arquivo Ink:

```ink
= Início da História
Este é o começo da sua aventura.

= Primeira Cena
O protagonista chega ao castelo.

* Entrar pela porta principal
  = Porta Principal
  Uma porta grande e imponente.

* Procurar uma entrada traseira
  = Entrada Traseira
  Uma entrada secreta atrás das árvores.

= Final
A aventura termina.
```

## 🎨 Funcionalidades

- ✅ Upload de arquivos Ink
- ✅ Parsing automático da estrutura
- ✅ Visualização em SVG
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
- Navegador moderno (Chrome, Firefox, Safari, Edge)

## 🔧 Desenvolvido com

- **Frontend**: HTML5, CSS3, JavaScript vanilla
- **Backend**: Node.js + Express
- **Visualização**: SVG nativo
- **Estilo**: Gradientes modernos e design responsivo

## 📄 Licença

MIT
