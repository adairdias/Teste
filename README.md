# ArbiTrack — Comparador de Odds e Detector de Arbitragem

Aplicativo web que compara odds em múltiplas casas de apostas (incluindo Betfair) para encontrar oportunidades de **arbitragem esportiva** — apostas em todos os resultados de um evento com lucro garantido.

## Como funciona

Quando a soma das probabilidades implícitas das melhores odds disponíveis é menor que 100%, existe uma oportunidade de arbitragem:

```
1/odd_A + 1/odd_B < 1  →  há lucro garantido

Exemplo:
  Betfair: Alcaraz 2.10  →  1/2.10 = 47.6%
  Pinnacle: Sinner  2.20  →  1/2.20 = 45.5%
  Total: 93.1%  →  Lucro de 6.9% em qualquer resultado
```

## Funcionalidades

- **Simulador**: insira odds de 2 ou 3 casas manualmente e calcule se há arbitragem
- **Scanner ao vivo**: varre eventos reais usando The Odds API (agrega Betfair, Pinnacle, Bet365 e outros)
- Cálculo automático de **quanto apostar em cada resultado**
- Modo **demonstração** funciona sem API key

## Instalação

### Requisitos
- Python 3.11+
- pip

### Rodando

```bash
chmod +x start.sh
./start.sh
```

Acesse: http://localhost:8000

### Modo ao vivo (dados reais)

1. Crie uma conta em https://the-odds-api.com (free tier: 500 req/mês)
2. Edite `backend/.env`:
   ```
   ODDS_API_KEY=sua_chave_aqui
   ```
3. Reinicie o servidor

## Estrutura

```
├── backend/
│   ├── main.py          # API FastAPI
│   ├── arbitrage.py     # Engine de cálculo de arbitragem
│   ├── odds_fetcher.py  # Integração com The Odds API e Betfair
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── start.sh
```

## Sobre arbitragem

A arbitragem esportiva é legal e funciona explorando diferenças de odds entre casas. As casas, no entanto, tendem a limitar ou fechar contas de apostadores identificados como "arbers". Recomendações:

- Aposte valores moderados
- Varie as casas utilizadas  
- Verifique as odds diretamente nas casas antes de confirmar (mudam rapidamente)
- Respeite os limites de aposta de cada casa

## APIs suportadas

| Fonte | Tipo | Casas incluídas |
|-------|------|-----------------|
| [The Odds API](https://the-odds-api.com) | Agregador | Betfair, Pinnacle, Bet365, Unibet, 1xBet e +40 |
| Betfair Exchange (via The Odds API) | Exchange | Betfair EU/UK |
