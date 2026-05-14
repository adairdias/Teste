const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys')
const { Boom } = require('@hapi/boom')
const express = require('express')
const qrcode = require('qrcode')
const path = require('path')
const P = require('pino')

const app = express()
app.use(express.json())
app.use(express.static(path.join(__dirname, 'public')))

let sock = null
let qrData = null
let isConnected = false
let membros = []
let grupoNome = ''

async function conectar() {
    const { state, saveCreds } = await useMultiFileAuthState('sessao_wpp')
    let version
    try {
        const r = await fetchLatestBaileysVersion()
        version = r.version
    } catch {
        version = [2, 3000, 1015901307]
    }

    sock = makeWASocket({
        version,
        auth: state,
        printQRInTerminal: true,
        logger: P({ level: 'silent' }),
        browser: ['Extrator', 'Chrome', '1.0.0'],
    })

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update
        if (qr) {
            qrData = qr
            isConnected = false
            console.log('[qr] Novo QR code gerado — abra o app para escanear')
        }
        if (connection === 'close') {
            isConnected = false
            const code = lastDisconnect?.error?.output?.statusCode
            if (code !== DisconnectReason.loggedOut) {
                console.log('[!] Reconectando...')
                setTimeout(conectar, 3000)
            } else {
                console.log('[!] Sessão encerrada. Reinicie o app.')
            }
        } else if (connection === 'open') {
            isConnected = true
            qrData = null
            console.log('[ok] WhatsApp conectado!')
        }
    })

    sock.ev.on('creds.update', saveCreds)
}

// ── Rotas ──────────────────────────────────────────────────────────────────────

app.get('/api/status', (req, res) => {
    res.json({ conectado: isConnected, tem_qr: !!qrData })
})

app.get('/api/qr', async (req, res) => {
    if (!qrData) return res.json({ qr: null })
    try {
        const qrImg = await qrcode.toDataURL(qrData)
        res.json({ qr: qrImg })
    } catch (e) {
        res.status(500).json({ erro: e.message })
    }
})

app.get('/api/grupos', async (req, res) => {
    if (!isConnected) return res.status(400).json({ erro: 'WhatsApp não conectado' })
    try {
        const grupos = await sock.groupFetchAllParticipating()
        const lista = Object.values(grupos)
            .map(g => ({ id: g.id, nome: g.subject, total: g.participants.length }))
            .sort((a, b) => a.nome.localeCompare(b.nome))
        res.json({ grupos: lista })
    } catch (e) { res.status(400).json({ erro: e.message }) }
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
    } catch (e) { res.status(400).json({ erro: e.message }) }
})

app.post('/api/criar-grupo', async (req, res) => {
    const { nome } = req.body
    if (!membros.length) return res.status(400).json({ erro: 'Extraia os membros primeiro' })
    if (!nome?.trim()) return res.status(400).json({ erro: 'Informe o nome do grupo' })
    try {
        const ids = membros.map(m => m.id).slice(0, 1023) // limite WhatsApp: 1024
        const result = await sock.groupCreate(nome.trim(), ids)
        res.json({ ok: true, id: result.id, total: ids.length })
    } catch (e) { res.status(400).json({ erro: e.message }) }
})

app.get('/api/link-convite', async (req, res) => {
    const { grupo_id } = req.query
    if (!grupo_id) return res.status(400).json({ erro: 'Informe o grupo' })
    try {
        const code = await sock.groupInviteCode(grupo_id)
        res.json({ link: `https://chat.whatsapp.com/${code}` })
    } catch (e) { res.status(400).json({ erro: e.message }) }
})

// ── Iniciar ────────────────────────────────────────────────────────────────────
conectar().then(() => {
    app.listen(3000, '0.0.0.0', () => {
        console.log('\n' + '='.repeat(50))
        console.log('  Extrator WhatsApp iniciado!')
        console.log('  Abra o navegador e acesse:')
        console.log('  http://localhost:3000')
        console.log('='.repeat(50) + '\n')
    })
}).catch(e => {
    console.error('Erro ao iniciar:', e)
    process.exit(1)
})
