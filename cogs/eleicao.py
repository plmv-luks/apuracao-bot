import json
import logging
from pathlib import Path

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

ESTADO = Path("data/apuracao.json")
BARRA = 20


def fmt(n):
    return f"{int(n):,}".replace(",", ".")


def nome_bonito(nome):
    nome = nome.title()
    for lig in ("Da", "De", "Do", "Das", "Dos", "E"):
        nome = nome.replace(f" {lig} ", f" {lig.lower()} ")
    return nome


def barra(pct):
    cheio = round(float(pct.replace(",", ".")) / 100 * BARRA)
    return "█" * cheio + "░" * (BARRA - cheio)


class Apuracao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        cfg = bot.config
        self.canal_id = cfg["canal_id"]
        self.eleicao = cfg["eleicoes"][cfg["turno"]]
        self.url = (
            f"https://resultados.tse.jus.br/oficial/ele2026/{self.eleicao}"
            f"/dados/br/br-c0001-e{self.eleicao:06d}-u.json"
        )
        self.intervalo = cfg.get("intervalo", 30)
        self.max_detalhado = cfg.get("max_detalhado", 4)
        self.candidatos = {str(n) for n in cfg.get("candidatos") or []}
        self.etag = None
        self.dados = None
        self.msg = None
        self.msg_id = None

    async def cog_load(self):
        try:
            estado = json.loads(ESTADO.read_text(encoding="utf-8"))
            if estado["canal_id"] == self.canal_id and estado["eleicao"] == self.eleicao:
                self.msg_id = estado["mensagem_id"]
        except (OSError, ValueError, KeyError):
            pass
        self.sessao = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))
        self.atualizar.change_interval(seconds=self.intervalo)
        self.atualizar.start()

    async def cog_unload(self):
        self.atualizar.cancel()
        await self.sessao.close()

    async def canal(self):
        return self.bot.get_channel(self.canal_id) or await self.bot.fetch_channel(self.canal_id)

    async def buscar(self):
        headers = {"User-Agent": "apuracao-bot/1.0"}
        if self.etag:
            headers["If-None-Match"] = self.etag
        async with self.sessao.get(self.url, headers=headers) as resp:
            if resp.status == 304:
                return False
            resp.raise_for_status()
            self.etag = resp.headers.get("ETag")
            self.dados = json.loads(await resp.text(encoding="utf-8-sig"))
        return True

    def montar_embed(self, dados):
        candidatos = []
        for agr in dados["carg"][0]["agr"]:
            for partido in agr["par"]:
                for cand in partido["cand"]:
                    if self.candidatos and cand["n"] not in self.candidatos:
                        continue
                    candidatos.append((cand, partido["sg"]))
        candidatos.sort(key=lambda c: (-int(c[0]["vap"]), int(c[0]["seq"])))

        blocos = []
        resto = []
        for pos, (cand, sigla) in enumerate(candidatos, start=1):
            nome = nome_bonito(cand["nmu"])
            if pos > self.max_detalhado:
                resto.append(f"{pos}. {nome}  ·  {sigla} {cand['n']}  ·  {cand['pvap']}%  ·  {fmt(cand['vap'])}")
                continue
            titulo = f"**{pos}. {nome}**  ·  {sigla} {cand['n']}"
            if cand["e"] == "s":
                titulo += f"  ·  {cand['st']}"
            blocos.append(f"{titulo}\n`{barra(cand['pvap'])}` {cand['pvap']}%\n{fmt(cand['vap'])} votos")
        if resto:
            blocos.append("\n".join(resto))

        s = dados["s"]
        v = dados["v"]
        embed = discord.Embed(
            title=f"Apuração  ·  Presidente  ·  {dados['t']}º turno",
            description="\n\n".join(blocos) or "Nenhum candidato da lista do config.yaml foi encontrado.",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="Seções totalizadas",
            value=f"`{barra(s['pst'])}` {s['pst']}%\n{fmt(s['st'])} de {fmt(s['ts'])}",
            inline=False,
        )
        embed.add_field(name="Votos válidos", value=f"{fmt(v['vv'])}\n{v['pvvc']}%")
        embed.add_field(name="Brancos", value=f"{fmt(v['vb'])}\n{v['pvb']}%")
        embed.add_field(name="Nulos", value=f"{fmt(v['tvn'])}\n{v['ptvn']}%")
        embed.set_footer(text=f"Fonte: TSE  ·  atualizado em {dados['dg']} às {dados['hg']}")
        return embed

    async def publicar(self):
        embed = self.montar_embed(self.dados)
        if self.msg:
            try:
                await self.msg.edit(embed=embed)
            except discord.NotFound:
                self.msg = None
        if not self.msg:
            self.msg = await (await self.canal()).send(embed=embed)
        ESTADO.parent.mkdir(exist_ok=True)
        ESTADO.write_text(
            json.dumps({"canal_id": self.canal_id, "mensagem_id": self.msg.id, "eleicao": self.eleicao}),
            encoding="utf-8",
        )

    @tasks.loop(seconds=30)
    async def atualizar(self):
        try:
            if await self.buscar():
                await self.publicar()
        except Exception as e:
            log.warning("falhou ao atualizar a apuração: %r", e)

    @atualizar.before_loop
    async def antes(self):
        await self.bot.wait_until_ready()
        if self.msg_id:
            try:
                self.msg = await (await self.canal()).fetch_message(self.msg_id)
            except discord.HTTPException:
                pass  # mensagem sumiu, cria outra no primeiro ciclo

    @app_commands.command(name="apuracao", description="Mostra a apuração atual da eleição presidencial")
    async def apuracao(self, interaction: discord.Interaction):
        if not self.dados:
            return await interaction.response.send_message("Ainda não recebi dados do TSE, tenta de novo daqui a pouco.", ephemeral=True)
        await interaction.response.send_message(embed=self.montar_embed(self.dados), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Apuracao(bot))
