#!/usr/bin/env python3
"""Gera enfeites de lápis (pencil toppers) paramétricos em STL.

Modelo disponível: cabine telefônica britânica (K6), a peça mais
geométrica do conjunto e a que sai bem gerada por perfil.

A peça é construída como um perfil de revolução quadrada: uma lista de
(altura, meia-largura) que define a silhueta, com um furo cego partindo
de baixo para encaixar o lápis.

Uso:
    python tools/enfeite_lapis.py cabine
    python tools/enfeite_lapis.py cabine --lapis 7.8 --altura-total 40
"""
import argparse
import math
import os
import struct

# ------------------------------------------------------------------ contornos --


def _quadrado(meia_largura: float, z: float, por_lado: int, recuo: float = 0.0) -> list[tuple]:
    """Contorno quadrado amostrado com `por_lado` pontos em cada aresta,
    no sentido anti-horário visto de cima.

    Com `recuo` > 0, o miolo de cada face é puxado para dentro, mas os
    cantos e o centro ficam salientes — é isso que dá os montantes
    verticais entre os vidros. Sem isso, o recuo some na face plana e a
    janela só apareceria na silhueta.
    """
    w = meia_largura
    cantos = [(w, -w), (w, w), (-w, w), (-w, -w)]
    # Direção para fora de cada lado, na ordem dos cantos acima.
    fora = [(1, 0), (0, 1), (-1, 0), (0, -1)]

    def saliente(t: float) -> bool:
        """Perto do canto (10%) ou do montante central (±6%)."""
        return t < 0.10 or t > 0.90 or 0.44 < t < 0.56

    pontos = []
    for i in range(4):
        a, b = cantos[i], cantos[(i + 1) % 4]
        fx, fy = fora[i]
        for k in range(por_lado):
            t = k / por_lado
            x = a[0] + (b[0] - a[0]) * t
            y = a[1] + (b[1] - a[1]) * t
            if recuo and not saliente(t):
                x -= fx * recuo
                y -= fy * recuo
            pontos.append((x, y, z))
    return pontos


def _circulo(raio: float, z: float, n: int) -> list[tuple]:
    return [
        (raio * math.cos(2 * math.pi * i / n), raio * math.sin(2 * math.pi * i / n), z)
        for i in range(n)
    ]


# -------------------------------------------------------------------- faces --


def _tampa(pontos: list[tuple], z: float, para_cima: bool) -> list[tuple]:
    centro = (0.0, 0.0, z)
    n = len(pontos)
    if para_cima:
        return [(centro, pontos[i], pontos[(i + 1) % n]) for i in range(n)]
    return [(centro, pontos[(i + 1) % n], pontos[i]) for i in range(n)]


def _degenerado(t: tuple, eps: float = 1e-7) -> bool:
    """Triângulo de área nula. Aparece nos degraus onde os dois contornos
    coincidem — nos montantes, o recuo é zero e não há superfície ali.
    Deixá-los na malha quebra a contagem de arestas e o fatiador acusa
    a peça como aberta."""
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    return (nx * nx + ny * ny + nz * nz) < eps


def _coroa(externo: list[tuple], interno: list[tuple], para_cima: bool) -> list[tuple]:
    tris = []
    n = len(externo)
    for i in range(n):
        j = (i + 1) % n
        if para_cima:
            candidatos = [
                (externo[i], externo[j], interno[j]),
                (externo[i], interno[j], interno[i]),
            ]
        else:
            candidatos = [
                (externo[i], interno[j], externo[j]),
                (externo[i], interno[i], interno[j]),
            ]
        tris += [t for t in candidatos if not _degenerado(t)]
    return tris


def _parede(baixo: list[tuple], cima: list[tuple], para_fora: bool) -> list[tuple]:
    tris = []
    n = len(baixo)
    for i in range(n):
        j = (i + 1) % n
        if para_fora:
            tris.append((baixo[i], baixo[j], cima[j]))
            tris.append((baixo[i], cima[j], cima[i]))
        else:
            tris.append((baixo[i], cima[j], baixo[j]))
            tris.append((baixo[i], cima[i], cima[j]))
    return tris


# ---------------------------------------------------------------- construcao --


def construir(perfil: list[tuple], r_furo: float, z_furo: float, por_lado: int) -> list[tuple]:
    """Monta um sólido a partir do perfil [(z, meia_largura), ...].

    O furo do lápis é cego e abre na face de BAIXO, subindo até z_furo.
    Pontos consecutivos com o mesmo z viram degrau horizontal; com z
    diferente, viram parede inclinada.
    """
    n_pts = por_lado * 4
    tris = []

    z_base, hw_base, rec_base = perfil[0]
    z_topo, hw_topo, rec_topo = perfil[-1]

    if r_furo * 2 >= hw_base * 2 * 0.8:
        raise ValueError(
            f"Furo de {r_furo * 2:.1f} mm é grosso demais para uma base de "
            f"{hw_base * 2:.1f} mm — a parede ficaria fina demais."
        )
    if z_furo >= z_topo:
        raise ValueError("Furo do lápis mais alto que a peça.")

    # Face de baixo: anel entre o contorno externo e o furo.
    tris += _coroa(
        _quadrado(hw_base, z_base, por_lado, rec_base),
        _circulo(r_furo, z_base, n_pts),
        para_cima=False,
    )

    # Silhueta externa, degrau a degrau.
    for (z0, hw0, r0), (z1, hw1, r1) in zip(perfil, perfil[1:]):
        c0 = _quadrado(hw0, z0, por_lado, r0)
        c1 = _quadrado(hw1, z1, por_lado, r1)
        if abs(z1 - z0) < 1e-9:
            # Degrau horizontal: alargar aponta para baixo, estreitar para cima.
            if (hw1 - r1) > (hw0 - r0):
                tris += _coroa(c1, c0, para_cima=False)
            else:
                tris += _coroa(c0, c1, para_cima=True)
        else:
            tris += _parede(c0, c1, para_fora=True)

    # Topo maciço.
    tris += _tampa(_quadrado(hw_topo, z_topo, por_lado, rec_topo), z_topo, para_cima=True)

    # Furo do lápis: parede com normal para dentro e teto olhando para baixo.
    furo_baixo = _circulo(r_furo, z_base, n_pts)
    furo_cima = _circulo(r_furo, z_furo, n_pts)
    tris += _parede(furo_baixo, furo_cima, para_fora=False)
    tris += _tampa(furo_cima, z_furo, para_cima=False)

    return tris


def perfil_cabine(altura: float, largura: float) -> dict:
    """Silhueta da cabine K6, em frações da altura total.

    Retorna as três partes separadas por cor: corpo, placa e telhado.
    """
    h, w = altura, largura / 2

    def f(frac):
        return h * frac

    # (fração da altura, meia-largura)
    R = 0.6  # profundidade do recuo dos vidros

    corpo = [
        (f(0.00), w, 0.0),     # plinto maciço
        (f(0.07), w, 0.0),
        (f(0.07), w, R),       # começa a área envidraçada
        (f(0.22), w, R),
        (f(0.22), w, 0.0),     # travessa
        (f(0.25), w, 0.0),
        (f(0.25), w, R),
        (f(0.40), w, R),
        (f(0.40), w, 0.0),     # travessa
        (f(0.43), w, 0.0),
        (f(0.43), w, R),
        (f(0.58), w, R),
        (f(0.58), w, 0.0),     # travessa
        (f(0.61), w, 0.0),
        (f(0.61), w, R),
        (f(0.72), w, R),
        (f(0.72), w, 0.0),     # cornija
        (f(0.76), w, 0.0),
    ]
    placa = [
        (f(0.76), w, 0.0),
        (f(0.76), w + 0.35, 0.0),   # faixa TELEPHONE, levemente saliente
        (f(0.86), w + 0.35, 0.0),
        (f(0.86), w, 0.0),
    ]
    telhado = [
        (f(0.86), w, 0.0),
        (f(0.86), w + 0.5, 0.0),    # beiral
        (f(0.89), w + 0.5, 0.0),
        (f(0.93), w * 0.72, 0.0),   # água do telhado
        (f(0.97), w * 0.30, 0.0),
        (f(1.00), w * 0.12, 0.0),   # pináculo
    ]
    return {"corpo": corpo, "placa": placa, "telhado": telhado}


# ---------------------------------------------------------------------- STL --


def _normal(t):
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    c = math.sqrt(nx * nx + ny * ny + nz * nz)
    return (nx / c, ny / c, nz / c) if c else (0.0, 0.0, 0.0)


def escrever_stl(tris, caminho):
    with open(caminho, "wb") as f:
        f.write(b"Enfeite de lapis - tools/enfeite_lapis.py".ljust(80, b"\0"))
        f.write(struct.pack("<I", len(tris)))
        for t in tris:
            f.write(struct.pack("<3f", *_normal(t)))
            for v in t:
                f.write(struct.pack("<3f", *v))
            f.write(struct.pack("<H", 0))


def solido_simples(perfil, por_lado):
    """Parte sem furo (placa e telhado), fechada em cima e embaixo."""
    tris = []
    z0, hw0, r0 = perfil[0]
    z1, hw1, r1 = perfil[-1]
    tris += _tampa(_quadrado(hw0, z0, por_lado, r0), z0, para_cima=False)
    for (za, ha, ra), (zb, hb, rb) in zip(perfil, perfil[1:]):
        ca = _quadrado(ha, za, por_lado, ra)
        cb = _quadrado(hb, zb, por_lado, rb)
        if abs(zb - za) < 1e-9:
            if (hb - rb) > (ha - ra):
                tris += _coroa(cb, ca, para_cima=False)
            else:
                tris += _coroa(ca, cb, para_cima=True)
        else:
            tris += _parede(ca, cb, para_fora=True)
    tris += _tampa(_quadrado(hw1, z1, por_lado, r1), z1, para_cima=True)
    return tris


def main():
    p = argparse.ArgumentParser(description="Gera enfeites de lápis em STL.")
    p.add_argument("modelo", choices=["cabine"], help="Qual enfeite gerar")
    p.add_argument("--lapis", type=float, default=7.5,
                   help="Diâmetro do lápis, em mm (padrão: 7.5)")
    p.add_argument("--folga", type=float, default=0.4,
                   help="Folga do encaixe, em mm (padrão: 0.4)")
    p.add_argument("--altura-total", type=float, default=38.0,
                   help="Altura do enfeite, em mm (padrão: 38)")
    p.add_argument("--largura", type=float, default=20.0,
                   help="Largura da cabine, em mm (padrão: 20)")
    p.add_argument("--profundidade-furo", type=float, default=22.0,
                   help="Quanto o lápis entra, em mm (padrão: 22)")
    p.add_argument("--por-lado", type=int, default=16,
                   help="Pontos por aresta do quadrado (padrão: 16)")
    p.add_argument("--destino", default="output/enfeites")
    args = p.parse_args()

    os.makedirs(args.destino, exist_ok=True)
    r_furo = (args.lapis + args.folga) / 2

    partes = perfil_cabine(args.altura_total, args.largura)

    saidas = [
        ("1_corpo_VERMELHO", construir(
            partes["corpo"], r_furo, args.profundidade_furo, args.por_lado)),
        ("2_placa_BRANCA", solido_simples(partes["placa"], args.por_lado)),
        ("3_telhado_VERMELHO", solido_simples(partes["telhado"], args.por_lado)),
    ]

    print()
    for nome, tris in saidas:
        caminho = os.path.join(args.destino, f"cabine_{nome}.stl")
        escrever_stl(tris, caminho)
        pts = [v for t in tris for v in t]
        zs = [v[2] for v in pts]
        print(f"  {caminho}")
        print(f"      z {min(zs):5.1f} → {max(zs):5.1f} mm   ({len(tris)} triângulos)")

    print(f"\n  Cabine ........ {args.largura:.1f} x {args.largura:.1f} x "
          f"{args.altura_total:.1f} mm")
    print(f"  Furo do lápis . {args.lapis + args.folga:.1f} mm "
          f"(lápis {args.lapis:.1f} + folga {args.folga:.1f})")
    print(f"  Profundidade .. {args.profundidade_furo:.1f} mm\n")
    print("  Imprime em pé, sem suporte. O furo fica na primeira camada.")
    print("  Escreva TELEPHONE na faixa branca com a ferramenta de texto")
    print("  do Bambu Studio — sai melhor que texto gerado em malha.\n")


if __name__ == "__main__":
    main()
