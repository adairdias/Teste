const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys')
const { Boom } = require('@hapi/boom')
const express = require('express')
const path = require('path')
const P = require('pino')

const app = express()
app.use(express.json())
app.use(express.static(path.join(__dirname, 'public')))

let sock = null
let pairingCode = null
let isConnected = false
let membros = []
let grupoNome = ''

async function conectar(phone) {
    const { state, saveCreds } = await useMultiFileAuthState('sessao_wpp')
    let version
    try { version = (await fetchLatestBaileysVersion()).version }
    catch { version = [2, 3000, 1015901307] }

    sock = makeWASocket({
        version,
        auth: state,
        printQRInTerminal: false,
        logger: P({ level: 'silent' }),
        browser: ['Extrator', 'Chrome', '1.0.0'],
    })

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update

        if (qr && phone) {
            try {
                const digits = phone.replace(/\D/g, '')
                pairingCode = await sock.requestPairingCode(digits)
                console.log(`[código] ${pairingCode}`)
            } catch(e) {
                console.error('[!] Erro ao gerar código:', e.message)
            }
        }

        if (connection === 'close') {
            isConnected = false
            pairingCode = null
            const code = lastDisconnect?.error?.output?.statusCode
            if (code !== DisconnectReason.loggedOut) {
                console.log('[!] Reconectando...')
                setTimeout(() => conectar(phone), 3000)
            } else {
                console.log('[!] Sessão encerrada. Reinicie o app.')
                sock = null
            }
        } else if (connection === 'open') {
            isConnected = true
            pairingCode = null
            console.log('[ok] WhatsApp conectado!')
        }
    })

    sock.ev.on('creds.update', saveCreds)
}

// ── Rotas ──────────────────────────────────────────────────────────────────────

app.get('/api/status', (req, res) => {
    res.json({ conectado: isConnected, tem_codigo: !!pairingCode, codigo: pairingCode })
})

app.post('/api/iniciar', async (req, res) => {
    const { phone } = req.body
    if (!phone) return res.status(400).json({ erro: 'Informe o número com DDI' })
    if (sock) { res.json({ ok: true }); return }
    try {
        await conectar(phone)
        res.json({ ok: true })
    } catch(e) { res.status(400).json({ erro: e.message }) }
})

app.get('/api/grupos', async (req, res) => {
    if (!isConnected) return res.status(400).json({ erro: 'WhatsApp não conectado' })
    try {
        const grupos = await sock.groupFetchAllParticipating()
        const lista = Object.values(grupos)
            .map(g => ({ id: g.id, nome: g.subject, total: g.participants.length }))
            .sort((a, b) => a.nome.localeCompare(b.nome))
        res.json({ grupos: lista })
    } catch(e) { res.status(400).json({ erro: e.message }) }
})

app.post('/api/extrair', async (req, res) => {
    const { grupo_id } = req.body
    if (!isConnected) return res.status(400).json({ erro: 'WhatsApp não conectado' })
    try {
        const meta = await sock.groupMetadata(grupo_id)
        grupoNome = meta.subject
        membros = meta.participants.map(p => ({
            id: p.id,
            numero: p.id.split('@')[0],
            admin: !!p.admin,
        }))
        res.json({ total: membros.length, nome: grupoNome })
    } catch(e) { res.status(400).json({ erro: e.message }) }
})

app.post('/api/criar-grupo', async (req, res) => {
    const { nome } = req.body
    if (!membros.length) return res.status(400).json({ erro: 'Extraia os membros primeiro' })
    if (!nome?.trim()) return res.status(400).json({ erro: 'Informe o nome do grupo' })
    try {
        const ids = membros.map(m => m.id).slice(0, 1023)
        const result = await sock.groupCreate(nome.trim(), ids)
        res.json({ ok: true, id: result.id, total: ids.length })
    } catch(e) { res.status(400).json({ erro: e.message }) }
})

app.get('/api/link-convite', async (req, res) => {
    const { grupo_id } = req.query
    if (!grupo_id) return res.status(400).json({ erro: 'Informe o grupo' })
    try {
        const code = await sock.groupInviteCode(grupo_id)
        res.json({ link: `https://chat.whatsapp.com/${code}` })
    } catch(e) { res.status(400).json({ erro: e.message }) }
})

// ── Iniciar ────────────────────────────────────────────────────────────────────
// Tenta reconectar sessão salva automaticamente
useMultiFileAuthState('sessao_wpp').then(({ state }) => {
    if (state.creds.registered) {
        console.log('[info] Sessão salva encontrada, reconectando...')
        conectar(null)
    }
}).catch(() => {})

app.listen(3000, '0.0.0.0', () => {
    console.log('\n' + '='.repeat(50))
    console.log('  Extrator WhatsApp iniciado!')
    console.log('  Abra o navegador e acesse:')
    console.log('  http://localhost:3000')
    console.log('='.repeat(50) + '\n')
})
