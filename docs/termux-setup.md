# Rodando Claude Code no tablet Android (Termux)

Guia para ter o Claude Code rodando direto no tablet, com acesso aos
arquivos do aparelho — sem root.

## Por que precisa do proot-distro

O Claude Code distribui um binário nativo compilado para **glibc**
(`linux-arm64`). O Android usa outra biblioteca de C, a **Bionic**, e não
existe build oficial para `android-arm64`. Por isso instalar direto no
Termux falha com erros como `unexpected e_type` ou "unsupported platform".

A solução é criar um Ubuntu completo dentro do Termux com `proot-distro`
(um sandbox, sem root), que fornece a glibc. Aí o instalador oficial
funciona normalmente.

> Isto **não é um setup oficialmente suportado** pela Anthropic. Funciona,
> mas pode quebrar em atualizações futuras.

## 1. Instalar o Termux

Baixe pelo **F-Droid** ou pelas releases do GitHub:

- https://f-droid.org/packages/com.termux/
- https://github.com/termux/termux-app/releases

**Não use a versão da Play Store** — está desatualizada e o `pkg` quebra.

## 2. Preparar o Termux

```bash
pkg update && pkg upgrade -y
pkg install proot-distro -y
termux-setup-storage   # autorize o acesso a arquivos quando pedir
```

O `termux-setup-storage` cria `~/storage/shared`, que aponta para a
memória interna do tablet (Downloads, DCIM, etc.).

## 3. Instalar o Ubuntu

```bash
proot-distro install ubuntu
```

Baixa ~500MB. Reserve uns 2-3GB livres no total.

## 4. Entrar e instalar as dependências

```bash
proot-distro login ubuntu
```

Já dentro do Ubuntu:

```bash
apt update && apt upgrade -y
apt install -y curl git python3 python3-pip python3-venv ffmpeg
```

## 5. Instalar o Claude Code

Ainda dentro do Ubuntu:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Confirme:

```bash
claude --version
```

## 6. Fazer login

```bash
claude
```

O login abre o navegador do Android para autorizar. Se o fluxo do
navegador travar (acontece em alguns aparelhos), use uma chave de API:

```bash
export ANTHROPIC_API_KEY="sua-chave-aqui"
```

Para deixar permanente, adicione essa linha no `~/.bashrc` do Ubuntu.

## 7. Acessar os arquivos do tablet

Dentro do Ubuntu, a memória do aparelho fica em:

```
/sdcard
```

Então os vídeos que você gravou estão em algo como
`/sdcard/DCIM/Camera` ou `/sdcard/Download`.

Para trabalhar direto numa pasta do aparelho:

```bash
proot-distro login ubuntu --work-dir /sdcard/Download
```

## 8. Atalho para facilitar

No Termux (fora do Ubuntu), adicione ao `~/.bashrc`:

```bash
alias cc='proot-distro login ubuntu --work-dir "$(pwd)"'
```

Recarregue com `source ~/.bashrc`. Depois é só digitar `cc` para cair no
Ubuntu já na pasta em que você está.

## 9. Clonar este projeto no tablet

Dentro do Ubuntu:

```bash
cd ~
git clone https://github.com/martinscaio1995-hub/Tablet.git
cd Tablet
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Como você instalou o `ffmpeg` no passo 4, o pipeline de vídeo roda
inteiro no tablet — e a pasta `assets/` pode receber clipes copiados
direto de `/sdcard/DCIM/Camera`.

## Dicas e problemas comuns

| Problema | Solução |
|---|---|
| Termux mata o processo em segundo plano | Rode `termux-wake-lock` antes de tarefas longas |
| Bateria drenando rápido | Normal em uso intenso; mantenha na tomada |
| `unexpected e_type` ao rodar `claude` | Você está fora do Ubuntu — rode `proot-distro login ubuntu` primeiro |
| Travamento no startup com Node v24 | Não se aplica aqui: o instalador oficial usa binário nativo, sem Node |
| `/sdcard` vazio dentro do Ubuntu | Faltou rodar `termux-setup-storage` no Termux e autorizar a permissão |

## Comparação com a máquina na nuvem

| | Nuvem (Claude Code web) | Termux + Ubuntu |
|---|---|---|
| Instalação | nenhuma | ~20 min |
| Acessa arquivos do tablet | não | sim |
| Desempenho | 4 CPUs / 15GB RAM | o do tablet |
| Suporte oficial | sim | não |
| Consumo de bateria | zero | alto |

Renderizar vídeo é pesado — para o pipeline deste projeto, a nuvem tende
a ser mais rápida. O Termux compensa quando você precisa mexer em
arquivos que já estão no aparelho.
