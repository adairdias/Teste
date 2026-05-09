"""
Cria um novo grupo no Telegram e adiciona os membros extraídos pelo extrator.py.

Uso:
    python criar_grupo.py membros_NomeDoGrupo.json "Nome do Novo Grupo"
"""

import json
import sys
import asyncio
import time
from telethon import TelegramClient
from telethon.tl.functions.channels import CreateChannelRequest, InviteToChannelRequest
from telethon.tl.functions.messages import AddChatUserRequest, CreateChatRequest
from telethon.errors import (
    FloodWaitError,
    UserPrivacyRestrictedError,
    UserNotMutualContactError,
)

# Mesmos valores usados no extrator.py
API_ID = 0
API_HASH = ""
PHONE = ""

# Máximo de usuários adicionados por vez (limite do Telegram)
LOTE = 10
PAUSA_ENTRE_LOTES = 5  # segundos


async def adicionar_em_lotes(client, canal, usernames):
    adicionados = 0
    falhas = []

    for i in range(0, len(usernames), LOTE):
        lote = usernames[i: i + LOTE]
        entidades = []

        for username in lote:
            try:
                entidade = await client.get_entity(username)
                entidades.append(entidade)
            except Exception as e:
                print(f"  [!] Não encontrado: @{username} — {e}")
                falhas.append(username)

        if not entidades:
            continue

        try:
            await client(InviteToChannelRequest(canal, entidades))
            adicionados += len(entidades)
            print(f"  Adicionados {adicionados} até agora...")
        except FloodWaitError as e:
            print(f"  FloodWait: aguardando {e.seconds}s...")
            await asyncio.sleep(e.seconds)
            # tenta novamente o mesmo lote
            try:
                await client(InviteToChannelRequest(canal, entidades))
                adicionados += len(entidades)
            except Exception as e2:
                print(f"  Falha no lote após espera: {e2}")
                falhas.extend([u.username for u in entidades if u.username])
        except (UserPrivacyRestrictedError, UserNotMutualContactError) as e:
            print(f"  Privacidade bloqueou alguns membros do lote.")
            falhas.extend([u.username for u in entidades if u.username])
        except Exception as e:
            print(f"  Erro no lote: {e}")
            falhas.extend([u.username for u in entidades if u.username])

        await asyncio.sleep(PAUSA_ENTRE_LOTES)

    return adicionados, falhas


async def main():
    if len(sys.argv) < 3:
        print("Uso: python criar_grupo.py <arquivo.json> \"Nome do Grupo\"")
        sys.exit(1)

    arquivo_json = sys.argv[1]
    nome_grupo = sys.argv[2]

    with open(arquivo_json, encoding="utf-8") as f:
        membros = json.load(f)

    usernames = [m["username"] for m in membros if m.get("username") and not m.get("bot")]

    print(f"Membros com @username (excluindo bots): {len(usernames)}")
    print(f"Membros sem @username (serão ignorados): {len(membros) - len(usernames)}")

    async with TelegramClient("sessao_extrator", API_ID, API_HASH) as client:
        await client.start(phone=PHONE)

        # Cria como supergrupo (megagroup=True) para suportar muitos membros
        print(f"\nCriando supergrupo: {nome_grupo}")
        resultado = await client(CreateChannelRequest(
            title=nome_grupo,
            about="",
            megagroup=True,
        ))
        canal = resultado.chats[0]
        print(f"Supergrupo criado com ID: {canal.id}")

        print("\nAdicionando membros...")
        adicionados, falhas = await adicionar_em_lotes(client, canal, usernames)

        print(f"\nConcluído!")
        print(f"  Adicionados com sucesso : {adicionados}")
        print(f"  Falhas (privacidade etc) : {len(falhas)}")
        if falhas:
            print(f"  Usuários com falha: {', '.join('@' + u for u in falhas)}")


if __name__ == "__main__":
    asyncio.run(main())
