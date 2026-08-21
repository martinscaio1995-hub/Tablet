#!/usr/bin/env python3
"""Separa um STL que contém várias peças soltas em um arquivo por peça.

Muitos modelos vêm com o prato inteiro num único STL. Para atribuir uma
cor por peça no AMS é preciso que cada uma seja um objeto — este script
faz esse corte, agrupando triângulos por conectividade de vértices.

Uso:
    python tools/separar_pecas.py prato.stl
    python tools/separar_pecas.py prato.stl --destino output --prefixo peca
"""
import argparse
import math
import os
import struct


def ler_stl(caminho: str) -> list[tuple]:
    with open(caminho, "rb") as f:
        f.read(80)
        n = struct.unpack("<I", f.read(4))[0]
        tris = []
        for _ in range(n):
            f.read(12)
            tris.append(tuple(struct.unpack("<3f", f.read(12)) for _ in range(3)))
            f.read(2)
    return tris


def _normal(t: tuple) -> tuple:
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    comp = math.sqrt(nx * nx + ny * ny + nz * nz)
    return (nx / comp, ny / comp, nz / comp) if comp else (0.0, 0.0, 0.0)


def escrever_stl(triangulos: list[tuple], caminho: str) -> None:
    with open(caminho, "wb") as f:
        f.write(b"Peca separada por tools/separar_pecas.py".ljust(80, b"\0"))
        f.write(struct.pack("<I", len(triangulos)))
        for t in triangulos:
            f.write(struct.pack("<3f", *_normal(t)))
            for v in t:
                f.write(struct.pack("<3f", *v))
            f.write(struct.pack("<H", 0))


def separar(tris: list[tuple]) -> list[list[tuple]]:
    """Agrupa triângulos em peças pela conectividade dos vértices."""
    def q(v):
        return tuple(round(c, 3) for c in v)

    pai = {}

    def find(x):
        while pai[x] != x:
            pai[x] = pai[pai[x]]
            x = pai[x]
        return x

    def une(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            pai[ra] = rb

    for t in tris:
        vs = [q(v) for v in t]
        for v in vs:
            pai.setdefault(v, v)
        une(vs[0], vs[1])
        une(vs[1], vs[2])

    grupos = {}
    for t in tris:
        grupos.setdefault(find(q(t[0])), []).append(t)

    # Maior volume primeiro, que costuma ser a peça principal.
    def volume(g):
        return abs(sum(
            (t[0][0] * (t[1][1] * t[2][2] - t[2][1] * t[1][2])
             - t[1][0] * (t[0][1] * t[2][2] - t[2][1] * t[0][2])
             + t[2][0] * (t[0][1] * t[1][2] - t[1][1] * t[0][2])) / 6
            for t in g
        ))

    return sorted(grupos.values(), key=volume, reverse=True)


def main():
    p = argparse.ArgumentParser(description="Separa um STL multi-peça em arquivos.")
    p.add_argument("arquivo", help="STL de entrada")
    p.add_argument("--destino", default="output", help="Pasta de saída")
    p.add_argument("--prefixo", default=None, help="Prefixo dos arquivos")
    args = p.parse_args()

    os.makedirs(args.destino, exist_ok=True)
    prefixo = args.prefixo or os.path.splitext(os.path.basename(args.arquivo))[0]

    pecas = separar(ler_stl(args.arquivo))
    print(f"\n  {len(pecas)} peça(s) encontrada(s) em {args.arquivo}\n")

    for i, g in enumerate(pecas, start=1):
        pts = [v for t in g for v in t]
        dx = max(p[0] for p in pts) - min(p[0] for p in pts)
        dy = max(p[1] for p in pts) - min(p[1] for p in pts)
        dz = max(p[2] for p in pts) - min(p[2] for p in pts)
        caminho = os.path.join(args.destino, f"{prefixo}_{i}.stl")
        escrever_stl(g, caminho)
        print(f"  {caminho}")
        print(f"      {dx:6.1f} x {dy:6.1f} x {dz:6.1f} mm   ({len(g)} triângulos)")
    print()


if __name__ == "__main__":
    main()
