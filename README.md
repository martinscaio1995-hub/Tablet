# Tablet como computador

Configuração para transformar um tablet Android num computador de verdade:
ele fica ligado rodando os projetos, e o celular o comanda por SSH.

## Rápido

No **Termux do tablet** (não dentro do proot — veja a nota abaixo):

```sh
git clone https://github.com/martinscaio1995-hub/tablet.git ~/tablet-setup
cd ~/tablet-setup
bash setup.sh
```

No fim ele mostra a linha exata de conexão para usar no celular.

## O que o `setup.sh` faz

- Instala `openssh`, `termux-services`, `tmux`, `git` e utilitários de rede
- Configura o `sshd` na porta **8022** com login por chave e por senha
- Autoriza a chave pública do celular (`--chave "ssh-ed25519 ..."`)
- Liga o `sshd` como serviço supervisionado, que se religa sozinho se cair
- Cria o script de boot em `~/.termux/boot/` para subir junto com o tablet
- Ativa `termux-wake-lock` para o Android não matar o processo
- Instala o comando `tablet-status`

O script é **idempotente**: rodar de novo é seguro e conserta o que ficou pela
metade. Ele guarda o `sshd_config` original em `sshd_config.original` antes de
mexer em qualquer coisa.

## Comandos

| Comando | O que faz |
|---|---|
| `bash setup.sh` | Instala e configura tudo |
| `bash setup.sh --chave "ssh-ed25519 ..."` | Autoriza a chave do celular |
| `bash setup.sh --porta 2222` | Usa outra porta |
| `tablet-status` | Mostra IP, porta, estado do sshd e sessões tmux |

## Termux ≠ proot

Se o seu prompt é `root@localhost:~#`, você está numa distro Linux rodando
*dentro* do Termux (proot), e o `setup.sh` vai recusar rodar ali — o servidor
SSH tem que viver no Termux, uma camada acima. Digite `exit` para voltar ao
Termux antes de rodar o script.

Confira com `echo $PREFIX`: no Termux ele responde
`/data/data/com.termux/files/usr`; no proot vem vazio.

## Documentação

- [`docs/conectar-do-celular.md`](docs/conectar-do-celular.md) — passo a passo do
  lado do celular, chaves SSH, `tmux` e o que fazer quando a conexão cai
