# Conectar no tablet a partir do celular

O tablet é o computador: ele roda os projetos e fica ligado. O celular é só o
teclado e a tela — entra por SSH e comanda.

## Antes de tudo: Termux ou proot?

Isso confunde muita gente e quebra o setup.

- **Termux** é o app em si. O prompt costuma ser `~ $` e existe a variável
  `$PREFIX` apontando para `/data/data/com.termux/...`.
- **proot / Ubuntu / Debian** é uma distro Linux rodando *dentro* do Termux
  (`proot-distro login ubuntu`). O prompt vira `root@localhost:~#`.

O `setup.sh` do servidor SSH **precisa rodar no Termux**, não dentro do proot.
Se você estiver no proot, saia primeiro:

```sh
exit
```

Confirme onde está:

```sh
echo $PREFIX
# Termux  -> /data/data/com.termux/files/usr
# proot   -> vazio
```

## 1. No tablet

```sh
git clone https://github.com/martinscaio1995-hub/tablet.git ~/tablet-setup
cd ~/tablet-setup
bash setup.sh
```

No fim ele imprime a linha de conexão. Anote o **IP** e a **porta** (8022).

Depois disso, `tablet-status` mostra esses dados a qualquer momento.

## 2. No celular

Instale o Termux no celular também (ou um app como JuiceSSH) e conecte:

```sh
pkg install openssh
ssh -p 8022 u0_a123@192.168.0.42
```

Troque `u0_a123` e o IP pelos valores que o `setup.sh` mostrou. Na primeira vez
ele pergunta a senha — a que você definiu com `passwd` no tablet.

## 3. Entrar sem digitar senha

Ainda **no celular**, gere uma chave e mostre-a:

```sh
ssh-keygen -t ed25519 -C celular
cat ~/.ssh/id_ed25519.pub
```

Copie a linha inteira (começa com `ssh-ed25519`) e, **no tablet**, rode:

```sh
cd ~/tablet-setup
bash setup.sh --chave "ssh-ed25519 AAAA...cole-aqui... celular"
```

Pronto — a próxima conexão entra direto.

## 4. Trabalho que não morre quando a conexão cai

Esse é o ponto que faz o tablet virar computador de verdade. Sem isso, o
processo morre toda vez que o celular perde o Wi-Fi ou a tela apaga.

No tablet (via SSH), use `tmux`:

```sh
tmux new -s trabalho     # cria a sessão
# ... deixe seus programas rodando ...
# Ctrl+B depois D        -> sai deixando tudo rodando
```

Para voltar depois, de qualquer lugar:

```sh
tmux attach -t trabalho
```

O programa continua rodando no tablet mesmo com o celular desligado.

## 5. Se a conexão parar de funcionar

| Sintoma | Causa provável | Solução |
|---|---|---|
| `Connection refused` | sshd não está rodando | No tablet: `sv up sshd` ou `sshd` |
| `No route to host` | IP mudou (DHCP) | Rode `tablet-status` para ver o IP novo |
| Cai sozinho após uns minutos | Android matou o Termux | `termux-wake-lock` e desative a otimização de bateria do Termux |
| Não volta depois de reiniciar | Termux:Boot ausente | Instale o app **Termux:Boot** pela F-Droid e abra uma vez |

O IP mudar é o incômodo mais comum. Se cansar disso, dá para fixar o IP do
tablet no roteador ou usar Tailscale — aí o endereço nunca mais muda e funciona
fora de casa também.
