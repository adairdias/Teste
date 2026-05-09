import os
import json
import asyncio
import threading
from flask import Flask, request, jsonify, render_template, Response
from telethon import TelegramClient
from telethon.tl.functions.channels import CreateChannelRequest, InviteToChannelRequest
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty, Channel, Chat
from telethon.errors import (
    SessionPasswordNeededError, FloodWaitError,
    UserPrivacyRestrictedError, UserNotMutualContactError,
    PhoneCodeExpiredError, PhoneCodeInvalidError,
    ChatAdminRequiredError,
)

app = Flask(__name__)
app.secret_key = "extrator-telegram-local"

# Background asyncio loop — Telethon vive aqui
_loop = asyncio.new_event_loop()
threading.Thread(target=_loop.run_forever, daemon=True).start()

def run(coro, timeout=180):
    return asyncio.run_coroutine_threadsafe(coro, _loop).result(timeout=timeout)

# Estado global (app de usuário único local)
estado = {
    "client": None,
    "phone": None,
    "phone_code_hash": None,
    "membros": [],
    "grupo_nome": "",
}


# ── Operações Telegram (async) ────────────────────────────────────────────────

async def _conectar(api_id, api_hash, phone):
    client = TelegramClient("sessao_local", api_id, api_hash)
    await client.connect()
    estado["client"] = client
    estado["phone"] = phone

    if await client.is_user_authorized():
        return "autorizado"

    result = await client.send_code_request(phone)
    estado["phone_code_hash"] = result.phone_code_hash
    return "codigo_enviado"


async def _verificar(codigo):
    client = estado["client"]
    await client.sign_in(
        estado["phone"], codigo,
        phone_code_hash=estado["phone_code_hash"]
    )


async def _senha_2fa(senha):
    await estado["client"].sign_in(password=senha)


async def _listar_grupos():
    result = await estado["client"](GetDialogsRequest(
        offset_date=None, offset_id=0,
        offset_peer=InputPeerEmpty(), limit=200, hash=0,
    ))
    grupos = []
    for d in result.chats:
        if isinstance(d, (Channel, Chat)):
            grupos.append({
                "id": d.id,
                "title": d.title,
                "tipo": "Supergrupo/Canal" if isinstance(d, Channel) else "Grupo",
            })
    return grupos


async def _extrair(grupo_id):
    client = estado["client"]
    dialogs = await client.get_dialogs()
    target = next((d.entity for d in dialogs if d.entity.id == grupo_id), None)
    if target is None:
        raise ValueError("Grupo não encontrado")

    def _membro(u):
        return {
            "id": u.id,
            "username": u.username,
            "primeiro_nome": u.first_name or "",
            "ultimo_nome": u.last_name or "",
            "telefone": u.phone,
            "bot": bool(u.bot),
        }

    membros = []
    modo_agressivo = False
    try:
        async for u in client.iter_participants(target):
            membros.append(_membro(u))
    except ChatAdminRequiredError:
        # Não é admin: usa busca por letras/nomes (parcial, sem precisar de admin)
        modo_agressivo = True
        vistos = set()
        async for u in client.iter_participants(target, aggressive=True):
            if u.id not in vistos:
                vistos.add(u.id)
                membros.append(_membro(u))

    return membros, modo_agressivo


async def _criar_grupo_telegram(nome, usernames):
    client = estado["client"]
    result = await client(CreateChannelRequest(title=nome, about="", megagroup=True))
    canal = result.chats[0]

    adicionados, falhas = 0, []
    for i in range(0, len(usernames), 10):
        lote = usernames[i: i + 10]
        entidades = []
        for username in lote:
            try:
                entidades.append(await client.get_entity(username))
            except Exception:
                falhas.append(username)

        if entidades:
            try:
                await client(InviteToChannelRequest(canal, entidades))
                adicionados += len(entidades)
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
                try:
                    await client(InviteToChannelRequest(canal, entidades))
                    adicionados += len(entidades)
                except Exception:
                    falhas.extend(u.username for u in entidades if u.username)
            except (UserPrivacyRestrictedError, UserNotMutualContactError):
                falhas.extend(u.username for u in entidades if u.username)
            except Exception:
                falhas.extend(u.username for u in entidades if u.username)

        await asyncio.sleep(3)

    return adicionados, len(falhas)


# ── Rotas Flask ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/conectar", methods=["POST"])
def conectar():
    data = request.json
    try:
        api_id = int(data["api_id"])
        api_hash = data["api_hash"].strip()
        phone = data["phone"].strip()
        status = run(_conectar(api_id, api_hash, phone))
        return jsonify({"status": status})
    except Exception as e:
        return jsonify({"erro": str(e)}), 400


@app.route("/api/verificar", methods=["POST"])
def verificar():
    codigo = request.json.get("codigo", "").strip()
    try:
        run(_verificar(codigo))
        return jsonify({"status": "ok"})
    except SessionPasswordNeededError:
        return jsonify({"status": "senha_2fa"})
    except (PhoneCodeInvalidError, PhoneCodeExpiredError):
        return jsonify({"erro": "Código inválido ou expirado. Tente novamente."}), 400
    except Exception as e:
        return jsonify({"erro": str(e)}), 400


@app.route("/api/senha-2fa", methods=["POST"])
def senha_2fa():
    senha = request.json.get("senha", "")
    try:
        run(_senha_2fa(senha))
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"erro": "Senha incorreta."}), 400


@app.route("/api/grupos")
def grupos():
    try:
        result = run(_listar_grupos())
        return jsonify({"grupos": result})
    except Exception as e:
        return jsonify({"erro": str(e)}), 400


@app.route("/api/extrair", methods=["POST"])
def extrair():
    data = request.json
    grupo_id = int(data["grupo_id"])
    estado["grupo_nome"] = data["grupo_nome"]
    try:
        membros, modo_agressivo = run(_extrair(grupo_id), timeout=300)
        estado["membros"] = membros
        humanos = [m for m in membros if not m["bot"]]
        return jsonify({
            "total": len(membros),
            "humanos": len(humanos),
            "com_username": sum(1 for m in humanos if m["username"]),
            "com_telefone": sum(1 for m in humanos if m["telefone"]),
            "bots": len(membros) - len(humanos),
            "modo_agressivo": modo_agressivo,
        })
    except Exception as e:
        return jsonify({"erro": str(e)}), 400


@app.route("/api/criar-grupo", methods=["POST"])
def criar_grupo():
    nome = request.json.get("nome", "").strip()
    if not nome:
        return jsonify({"erro": "Informe o nome do grupo."}), 400

    usernames = [
        m["username"] for m in estado["membros"]
        if m.get("username") and not m.get("bot")
    ]
    try:
        adicionados, falhas = run(_criar_grupo_telegram(nome, usernames), timeout=600)
        return jsonify({"adicionados": adicionados, "falhas": falhas})
    except Exception as e:
        return jsonify({"erro": str(e)}), 400


@app.route("/api/links-whatsapp")
def links_whatsapp():
    link_grupo = request.args.get("link_grupo", "")
    links = []
    for m in estado["membros"]:
        if m.get("telefone") and not m.get("bot"):
            numero = m["telefone"].replace("+", "").replace(" ", "").replace("-", "")
            nome = f"{m.get('primeiro_nome', '')} {m.get('ultimo_nome', '')}".strip()
            texto = f"Olá! Te convido para entrar no nosso grupo: {link_grupo}" if link_grupo else "Olá!"
            links.append({
                "nome": nome or m.get("username") or str(m["id"]),
                "telefone": m["telefone"],
                "link": f"https://wa.me/{numero}?text={texto}",
            })
    return jsonify({"links": links})


@app.route("/api/download")
def download():
    membros = estado["membros"]
    nome = estado["grupo_nome"].replace(" ", "_") or "membros"
    conteudo = json.dumps(membros, ensure_ascii=False, indent=2)
    return Response(
        conteudo,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename=membros_{nome}.json"},
    )


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  Extrator Telegram iniciado!")
    print("  Abra o navegador e acesse:")
    print("  http://localhost:5000")
    print("=" * 50 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
