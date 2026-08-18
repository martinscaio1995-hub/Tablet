#!/usr/bin/env bash
#
# Configura o tablet (Termux) como servidor SSH, para ser acessado pelo celular.
#
# Uso no tablet:
#   bash setup.sh
#
# Opcional, já instalando a chave pública do celular:
#   bash setup.sh --chave "ssh-ed25519 AAAA... celular"
#
# O script é idempotente: rodar de novo é seguro e conserta o que estiver pela metade.

set -euo pipefail

SSHD_CONFIG="$PREFIX/etc/ssh/sshd_config"
AUTHORIZED_KEYS="$HOME/.ssh/authorized_keys"
BOOT_DIR="$HOME/.termux/boot"
PORTA=8022
CHAVE_PUBLICA=""

# ---------------------------------------------------------------- utilidades --

vermelho() { printf '\033[31m%s\033[0m\n' "$*"; }
verde()    { printf '\033[32m%s\033[0m\n' "$*"; }
amarelo()  { printf '\033[33m%s\033[0m\n' "$*"; }
titulo()   { printf '\n\033[1;36m== %s\033[0m\n' "$*"; }
passo()    { printf '   %s\n' "$*"; }

erro() {
  vermelho "ERRO: $*"
  exit 1
}

# ------------------------------------------------------------------ argumentos --

while [ $# -gt 0 ]; do
  case "$1" in
    --chave)
      CHAVE_PUBLICA="${2:-}"
      [ -n "$CHAVE_PUBLICA" ] || erro "--chave precisa vir seguido da chave pública."
      shift 2
      ;;
    --porta)
      PORTA="${2:-}"
      shift 2
      ;;
    -h|--ajuda|--help)
      sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      erro "Opção desconhecida: $1"
      ;;
  esac
done

# ----------------------------------------------------------- checagem do ambiente --

titulo "Verificando ambiente"

if [ -z "${PREFIX:-}" ] || [ "${PREFIX#*com.termux}" = "$PREFIX" ]; then
  erro "Este script precisa rodar dentro do Termux, no tablet."
fi
passo "Termux detectado em \$PREFIX = $PREFIX"
passo "Usuário: $(whoami)"

# -------------------------------------------------------------------- pacotes --

titulo "Instalando pacotes"

PACOTES="openssh termux-services tmux git nano procps iproute2 termux-api"

# Atualiza a lista de pacotes; não aborta o script se o espelho estiver instável.
if ! pkg update -y >/dev/null 2>&1; then
  amarelo "   Aviso: 'pkg update' falhou (espelho instável?). Seguindo mesmo assim."
fi

for pacote in $PACOTES; do
  if dpkg -s "$pacote" >/dev/null 2>&1; then
    passo "já instalado: $pacote"
  else
    passo "instalando: $pacote"
    pkg install -y "$pacote" >/dev/null || erro "Falha ao instalar '$pacote'."
  fi
done

# ------------------------------------------------------------ configuração sshd --

titulo "Configurando o servidor SSH"

[ -f "$SSHD_CONFIG" ] || erro "sshd_config não encontrado em $SSHD_CONFIG."

# Guarda uma cópia original na primeira execução, para poder voltar atrás.
if [ ! -f "$SSHD_CONFIG.original" ]; then
  cp "$SSHD_CONFIG" "$SSHD_CONFIG.original"
  passo "backup criado: $SSHD_CONFIG.original"
fi

# Define uma opção do sshd_config sem duplicar linhas: reescreve a existente
# (mesmo comentada) ou adiciona no fim se não houver nenhuma.
definir_opcao() {
  local chave="$1" valor="$2"
  if grep -qE "^[[:space:]]*#?[[:space:]]*${chave}[[:space:]]" "$SSHD_CONFIG"; then
    sed -i -E "s|^[[:space:]]*#?[[:space:]]*${chave}[[:space:]].*|${chave} ${valor}|" "$SSHD_CONFIG"
  else
    printf '%s %s\n' "$chave" "$valor" >> "$SSHD_CONFIG"
  fi
  passo "$chave $valor"
}

definir_opcao Port "$PORTA"
definir_opcao PubkeyAuthentication yes
definir_opcao PasswordAuthentication yes
definir_opcao PrintMotd yes

# ------------------------------------------------------------------- chave SSH --

titulo "Chave pública do celular"

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
touch "$AUTHORIZED_KEYS"
chmod 600 "$AUTHORIZED_KEYS"

if [ -n "$CHAVE_PUBLICA" ]; then
  if grep -qxF "$CHAVE_PUBLICA" "$AUTHORIZED_KEYS"; then
    passo "chave já estava autorizada"
  else
    printf '%s\n' "$CHAVE_PUBLICA" >> "$AUTHORIZED_KEYS"
    verde "   chave adicionada a $AUTHORIZED_KEYS"
  fi
else
  QTD_CHAVES=$(grep -c '^ssh-' "$AUTHORIZED_KEYS" 2>/dev/null || true)
  if [ "${QTD_CHAVES:-0}" -gt 0 ]; then
    passo "$QTD_CHAVES chave(s) já autorizada(s)"
  else
    amarelo "   Nenhuma chave autorizada ainda."
    amarelo "   Você vai entrar por senha agora e pode adicionar a chave depois"
    amarelo "   (veja docs/conectar-do-celular.md)."
  fi
fi

# ----------------------------------------------------------------------- senha --

titulo "Senha de acesso"

# No Termux não há /etc/shadow legível para checar; o jeito confiável é perguntar.
if [ -t 0 ]; then
  printf '   Definir/trocar a senha do Termux agora? [s/N] '
  read -r RESPOSTA
  case "$RESPOSTA" in
    s|S|sim|SIM)
      passwd
      verde "   senha definida"
      ;;
    *)
      passo "pulado — use 'passwd' quando quiser definir"
      ;;
  esac
else
  passo "sem terminal interativo — rode 'passwd' manualmente"
fi

# -------------------------------------------------------------------- serviços --

titulo "Ligando o sshd"

# termux-services mantém o sshd de pé e o religa se ele cair.
if [ -d "$PREFIX/var/service/sshd" ]; then
  sv-enable sshd >/dev/null 2>&1 || true
  sv up sshd    >/dev/null 2>&1 || true
  passo "serviço sshd habilitado via termux-services"
  amarelo "   Se ele não subir, feche e reabra o Termux uma vez (o supervisor"
  amarelo "   só inicia junto com uma nova sessão) e rode este script de novo."
fi

# Rede de segurança: se o serviço não pegou, sobe o sshd direto.
if ! pgrep -x sshd >/dev/null 2>&1; then
  sshd >/dev/null 2>&1 || true
  sleep 1
fi

if pgrep -x sshd >/dev/null 2>&1; then
  verde "   sshd está rodando"
else
  erro "sshd não subiu. Rode 'sshd -d' para ver o motivo."
fi

# --------------------------------------------------------- iniciar junto ao boot --

titulo "Iniciar sozinho quando o tablet ligar"

mkdir -p "$BOOT_DIR"
cat > "$BOOT_DIR/00-sshd.sh" <<'BOOT'
#!/data/data/com.termux/files/usr/bin/sh
# Mantém o Android de matar o Termux e sobe o servidor SSH no boot.
termux-wake-lock
sshd
BOOT
chmod +x "$BOOT_DIR/00-sshd.sh"
passo "script criado: $BOOT_DIR/00-sshd.sh"
amarelo "   Só funciona com o app Termux:Boot instalado (F-Droid) e aberto uma vez."

# ------------------------------------------------------------------- wake lock --

titulo "Evitando que o Android durma o Termux"

termux-wake-lock 2>/dev/null && passo "wake lock ativo" \
  || amarelo "   termux-wake-lock indisponível (instale o app Termux:API)"

# ------------------------------------------------------------- comando de status --

titulo "Instalando o comando 'tablet-status'"

mkdir -p "$PREFIX/bin"
if [ -f "$(dirname "$0")/bin/tablet-status" ]; then
  install -m 755 "$(dirname "$0")/bin/tablet-status" "$PREFIX/bin/tablet-status"
  passo "use 'tablet-status' a qualquer momento"
fi

# ------------------------------------------------------------------------ resumo --

titulo "Pronto"

IP=$(ip -4 addr show 2>/dev/null \
  | grep -oE 'inet [0-9.]+' \
  | awk '{print $2}' \
  | grep -v '^127\.' \
  | head -1)

echo
echo "   Do celular, conecte com:"
echo
if [ -n "${IP:-}" ]; then
  verde "     ssh -p $PORTA $(whoami)@$IP"
else
  amarelo "     ssh -p $PORTA $(whoami)@<IP-DO-TABLET>"
  amarelo "     (não consegui detectar o IP — rode 'tablet-status')"
fi
echo
echo "   Passo a passo do lado do celular: docs/conectar-do-celular.md"
echo
