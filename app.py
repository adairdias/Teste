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

# ── Credenciais fixas ─────────────────────────────────────────────────────────
API_ID   = 31023456
API_HASH = "0bf170523afd121d8db330c98d508f79"
PHONE_FILE = "telefone.txt"

app = Flask(__name__)
app.secret_key = "extrator-telegram-local"
app.json.ensure_ascii = True  # evita UnicodeEncodeError em headers HTTP

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


# ── Helpers de persistência ───────────────────────────────────────────────────

def ler_telefone():
    try:
        with open(PHONE_FILE) as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""

def salvar_telefone(phone):
    with open(PHONE_FILE, "w") as f:
        f.write(phone)


# ── Operações Telegram (async) ────────────────────────────────────────────────

async def _ensure_client():
    """Garante que o cliente está conectado; retorna True se já autorizado."""
    if estado["client"] is None:
        client = TelegramClient("sessao_local", API_ID, API_HASH)
        await client.connect()
        estado["client"] = client
        estado["phone"] = ler_telefone()
    return await estado["client"].is_user_authorized()


async def _conectar(phone):
    autorizado = await _ensure_client()
    if autorizado:
        return "autorizado"
    estado["phone"] = phone
    salvar_telefone(phone)
    result = await estado["client"].send_code_request(phone)
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
        if isinstance(d, Channel):
            tipo = "Supergrupo" if getattr(d, "megagroup", False) else "Canal"
        else:
            tipo = "Grupo"
        grupos.append({
            "id": d.id,
            "title": d.title,
            "tipo": tipo,
            "canal": isinstance(d, Channel) and not getattr(d, "megagroup", False),
        })
    return grupos


async def _extrair(grupo_id):
    client = estado["client"]
    dialogs = await client.get_dialogs()
    target = next((d.entity for d in dialogs if d.entity.id == grupo_id), None)
    if target is None:
        raise ValueError("Grupo não encontrado")

    # Canais de transmissão (não megagrupos) exigem ser admin para ver membros
    if isinstance(target, Channel) and not getattr(target, "megagroup", False):
        raise ValueError(
            "Este é um Canal de transmissão — assinantes não podem ver a lista de membros. "
            "Escolha um Grupo ou Supergrupo normal."
        )

    def _membro(u):
        return {
            "id": u.id,
            "access_hash": u.access_hash,  # necessário para adicionar sem @username
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
        modo_agressivo = True
        vistos = set()
        try:
            async for u in client.iter_participants(target, aggressive=True):
                if u.id not in vistos:
                    vistos.add(u.id)
                    membros.append(_membro(u))
        except Exception:
            pass  # Retorna o que conseguiu até agora

    if not membros and modo_agressivo:
        raise ValueError(
            "Não foi possível extrair membros. Você precisa ser admin do grupo, "
            "ou tente em um Grupo menor."
        )

    return membros, modo_agressivo


async def _criar_grupo_telegram(nome, membros):
    from telethon.tl.types import InputPeerUser
    client = estado["client"]
    result = await client(CreateChannelRequest(title=nome, about="", megagroup=True))
    canal = result.chats[0]
    print(f"\n[+] Grupo '{nome}' criado. Adicionando {len(membros)} membros...")

    # Monta entidades usando ID+access_hash
    entidades_todas = []
    for m in membros:
        try:
            if m.get("access_hash") is not None:
                entidades_todas.append(InputPeerUser(m["id"], m["access_hash"]))
            elif m.get("username"):
                entidades_todas.append(await client.get_entity(m["username"]))
        except Exception as e:
            print(f"  [!] Entidade não resolvida id={m['id']}: {e}")

    print(f"[+] Entidades prontas: {len(entidades_todas)}")

    adicionados, falhas = 0, 0
    for i in range(0, len(entidades_todas), 10):
        lote = entidades_todas[i: i + 10]
        try:
            await client(InviteToChannelRequest(canal, lote))
            adicionados += len(lote)
            print(f"  [ok] Adicionados: {adicionados}/{len(entidades_todas)}")
        except FloodWaitError as e:
            print(f"  [flood] Aguardando {e.seconds}s...")
            await asyncio.sleep(e.seconds)
            try:
                await client(InviteToChannelRequest(canal, lote))
                adicionados += len(lote)
                print(f"  [ok] Adicionados após espera: {adicionados}")
            except Exception as e2:
                falhas += len(lote)
                print(f"  [!] Falha no lote após espera: {e2}")
        except (UserPrivacyRestrictedError, UserNotMutualContactError) as e:
            falhas += len(lote)
            print(f"  [privacidade] {len(lote)} bloqueados: {e}")
        except Exception as e:
            falhas += len(lote)
            print(f"  [!] Erro no lote: {type(e).__name__}: {e}")

        await asyncio.sleep(3)

    print(f"\n[=] Concluído: {adicionados} adicionados, {falhas} falhas.\n")
    return adicionados, falhas


async def _adicionar_em_existente(grupo_destino_id, membros):
    from telethon.tl.types import InputPeerUser
    client = estado["client"]

    dialogs = await client.get_dialogs()
    target = next((d.entity for d in dialogs if d.entity.id == grupo_destino_id), None)
    if target is None:
        raise ValueError("Grupo destino não encontrado")

    # Descobre quem já está no grupo para não adicionar duplicatas
    ids_existentes = set()
    try:
        async for u in client.iter_participants(target):
            ids_existentes.add(u.id)
    except Exception:
        pass

    novos = [m for m in membros if m["id"] not in ids_existentes]
    pulados = len(membros) - len(novos)
    print(f"\n[+] {pulados} já estão no grupo. {len(novos)} para adicionar.")

    if not novos:
        return 0, 0, pulados

    entidades = []
    for m in novos:
        try:
            if m.get("access_hash") is not None:
                entidades.append(InputPeerUser(m["id"], m["access_hash"]))
            elif m.get("username"):
                entidades.append(await client.get_entity(m["username"]))
        except Exception as e:
            print(f"  [!] Entidade não resolvida: {e}")

    adicionados, falhas = 0, 0
    for i in range(0, len(entidades), 10):
        lote = entidades[i:i + 10]
        try:
            await client(InviteToChannelRequest(target, lote))
            adicionados += len(lote)
            print(f"  [ok] Adicionados: {adicionados}/{len(entidades)}")
        except FloodWaitError as e:
            print(f"  [flood] Aguardando {e.seconds}s...")
            await asyncio.sleep(e.seconds)
            try:
                await client(InviteToChannelRequest(target, lote))
                adicionados += len(lote)
            except Exception as e2:
                falhas += len(lote)
                print(f"  [!] Falha após espera: {e2}")
        except (UserPrivacyRestrictedError, UserNotMutualContactError):
            falhas += len(lote)
            print(f"  [privacidade] {len(lote)} bloqueados")
        except Exception as e:
            falhas += len(lote)
            print(f"  [!] Erro: {type(e).__name__}: {e}")

        await asyncio.sleep(3)

    print(f"[=] Concluído: {adicionados} adicionados, {falhas} falhas, {pulados} já estavam.\n")
    return adicionados, falhas, pulados

# ── Rotas Flask ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def status():
    """Verifica se já existe sessão válida. Chamado ao carregar a página."""
    try:
        autorizado = run(_ensure_client())
        return jsonify({
            "autorizado": autorizado,
            "phone": ler_telefone(),
        })
    except Exception as e:
        return jsonify({"autorizado": False, "phone": "", "erro": str(e)})


@app.route("/api/conectar", methods=["POST"])
def conectar():
    phone = request.json.get("phone", "").strip()
    try:
        status = run(_conectar(phone))
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
    except Exception:
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

    membros = [m for m in estado["membros"] if not m.get("bot")]
    try:
        adicionados, falhas = run(_criar_grupo_telegram(nome, membros), timeout=600)
        return jsonify({"adicionados": adicionados, "falhas": falhas})
    except Exception as e:
        return jsonify({"erro": str(e)}), 400


@app.route("/api/adicionar-existente", methods=["POST"])
def adicionar_existente():
    grupo_id = request.json.get("grupo_id")
    if not grupo_id:
        return jsonify({"erro": "Selecione um grupo destino."}), 400

    membros = [m for m in estado["membros"] if not m.get("bot")]
    try:
        adicionados, falhas, pulados = run(
            _adicionar_em_existente(int(grupo_id), membros), timeout=600
        )
        return jsonify({"adicionados": adicionados, "falhas": falhas, "pulados": pulados})
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
    # Remove emoji e chars não-ASCII do nome do arquivo (headers HTTP só aceitam latin-1)
    nome = estado["grupo_nome"].encode("ascii", "ignore").decode("ascii").replace(" ", "_").strip("_") or "membros"
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
