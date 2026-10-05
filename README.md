# apuracao-bot

bot de discord que acompanha a apuração da eleição presidencial pela api do TSE e mantém um único embed atualizado num canal.

ele consulta o json do TSE a cada 30 segundos, monta o embed com os candidatos ordenados por votos e edita sempre a mesma mensagem. o id dela fica salvo em `data/apuracao.json`, então depois de reiniciar ele pega a mensagem de volta. tem também o slash command `/apuracao`, que mostra os números atuais só pra quem usou.

## rodando

```
pip install -r requirements.txt
```

crie um `.env`:

```
DISCORD_TOKEN=seu_token_aqui
```

mexa no `config.yaml` (canal, turno, candidatos) e rode:

```
python main.py
```

python 3.10+. o id da eleição e como achar ele estão comentados no próprio `config.yaml`, pro 2º turno é só trocar o `turno` pra 2.
