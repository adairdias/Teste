"""
Extrator de membros de grupo do Telegram.

Pré-requisitos:
    pip install telethon

Como obter API_ID e API_HASH:
    1. Acesse https://my.telegram.org
    2. Faça login com seu número de telefone
    3. Clique em "API development tools"
    4. Crie um app e copie API_ID e API_HASH
"""

import json
import asyncio
from telethon import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty, Channel, Chat

API_ID = 0          # substitua pelo seu api_id (número inteiro)
API_HASH = ""       # substitua pelo seu api_hash (string)
PHONE = ""          # seu número com DDI, ex: "+5511999999999"


async def listar_grupos(client):
    result = await client(GetDialogsRequest(
        offset_date=None,
        offset_id=0,
        offset_peer=InputPeerEmpty(),
        limit=200,
        hash=0,
    ))

    grupos = [
        d for d in result.chats
        if isinstance(d, (Channel, Chat))
    ]

    if not grupos:
        print("Nenhum grupo encontrado.")
        return None

    print("\nGrupos disponíveis:")
    for i, g in enumerate(grupos):
        tipo = "Canal/Supergrupo" if isinstance(g, Channel) else "Grupo"
        print(f"  [{i}] {g.title}  ({tipo})")

    idx = int(input("\nDigite o número do grupo: "))
    return grupos[idx]


async def extrair_membros(client, grupo):
    print(f"\nExtraindo membros de: {grupo.title} ...")
    membros = []

    async for usuario in client.iter_participants(grupo):
        membro = {
            "id": usuario.id,
            "username": usuario.username,
            "primeiro_nome": usuario.first_name,
            "ultimo_nome": usuario.last_name,
            "bot": usuario.bot,
        }
        membros.append(membro)

    return membros


async def main():
    async with TelegramClient("sessao_extrator", API_ID, API_HASH) as client:
        await client.start(phone=PHONE)

        grupo = await listar_grupos(client)
        if grupo is None:
            return

        membros = await extrair_membros(client, grupo)

        nome_arquivo = f"membros_{grupo.title.replace(' ', '_')}.json"
        with open(nome_arquivo, "w", encoding="utf-8") as f:
            json.dump(membros, f, ensure_ascii=False, indent=2)

        total = len(membros)
        com_username = sum(1 for m in membros if m["username"])
        print(f"\nConcluído!")
        print(f"  Total de membros : {total}")
        print(f"  Com @username    : {com_username}")
        print(f"  Sem @username    : {total - com_username}")
        print(f"  Arquivo salvo    : {nome_arquivo}")
        print("\nObs: membros sem @username não podem ser adicionados")
        print("     a um novo grupo diretamente.")


if __name__ == "__main__":
    asyncio.run(main())
