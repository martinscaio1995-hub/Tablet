#!/usr/bin/env python3
"""Gera uma base de display (STL) para peça vertical — berimbau, tótem,
troféu, qualquer coisa que precise ficar em pé.

Python puro, sem dependência nenhuma: roda no Termux/proot direto.

Uso:
    python tools/base_display.py                      # base padrão
    python tools/base_display.py --furo 12.4          # ajusta ao seu modelo
    python tools/base_display.py --diametro 95 --altura 22 --saida base.stl

MEÇA A VERGA com paquímetro (ou régua) na ponta que entra na base e passe
em --furo. O script já soma a folga de encaixe (--folga, padrão 0.4 mm),
então informe a medida real da peça, não a medida do furo.
"""
import argparse
import math
import struct

# ------------------------------------------------------------------ geometria --


def _circulo(raio: float, z: float, segmentos: int) -> list[tuple]:
    """Pontos de um círculo no plano Z, em sentido anti-horário visto de cima."""
    return [
        (
            raio * math.cos(2 * math.pi * i / segmentos),
            raio * math.sin(2 * math.pi * i / segmentos),
            z,
        )
        for i in range(segmentos)
    ]


def gerar_base(
    diametro_base: float,
    diametro_topo: float,
    altura: float,
    diametro_furo: float,
    profundidade_furo: float,
    segmentos: int,
) -> list[tuple]:
    """Monta a malha da base como lista de triângulos (3 vértices cada).

    A peça é um tronco de cone (base mais larga que o topo, para dar
    estabilidade e um acabamento melhor) com um furo cego no centro onde
    a verga encaixa.
    """
    r_base = diametro_base / 2
    r_topo = diametro_topo / 2
    r_furo = diametro_furo / 2
    z_furo = altura - profundidade_furo

    if z_furo <= 0:
        raise ValueError(
            f"Furo de {profundidade_furo} mm não cabe numa base de "
            f"{altura} mm. Aumente --altura ou reduza --profundidade."
        )
    if r_furo >= r_topo:
        raise ValueError(
            f"Furo de {diametro_furo} mm é maior que o topo de "
            f"{diametro_topo} mm. Aumente --diametro."
        )

    inferior = _circulo(r_base, 0.0, segmentos)
    superior = _circulo(r_topo, altura, segmentos)
    furo_topo = _circulo(r_furo, altura, segmentos)
    furo_fundo = _circulo(r_furo, z_furo, segmentos)

    centro_inferior = (0.0, 0.0, 0.0)
    centro_furo = (0.0, 0.0, z_furo)

    tris = []
    for i in range(segmentos):
        j = (i + 1) % segmentos

        # Face de baixo (normal para -Z): assenta na mesa de impressão.
        tris.append((centro_inferior, inferior[j], inferior[i]))

        # Parede externa cônica (normal para fora).
        tris.append((inferior[i], inferior[j], superior[j]))
        tris.append((inferior[i], superior[j], superior[i]))

        # Coroa do topo, entre a borda externa e o furo (normal para +Z).
        tris.append((superior[i], superior[j], furo_topo[j]))
        tris.append((superior[i], furo_topo[j], furo_topo[i]))

        # Parede do furo (normal para dentro, apontando ao eixo).
        tris.append((furo_topo[i], furo_topo[j], furo_fundo[j]))
        tris.append((furo_topo[i], furo_fundo[j], furo_fundo[i]))

        # Fundo do furo (normal para +Z).
        tris.append((centro_furo, furo_fundo[i], furo_fundo[j]))

    return tris


# ---------------------------------------------------------------------- STL --


def _normal(t: tuple) -> tuple:
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    comp = math.sqrt(nx * nx + ny * ny + nz * nz)
    return (nx / comp, ny / comp, nz / comp) if comp else (0.0, 0.0, 0.0)


def escrever_stl(triangulos: list[tuple], caminho: str) -> None:
    """Grava STL binário — bem menor que ASCII e aceito por todo fatiador."""
    with open(caminho, "wb") as f:
        f.write(b"Base de display gerada por tools/base_display.py".ljust(80, b"\0"))
        f.write(struct.pack("<I", len(triangulos)))
        for t in triangulos:
            f.write(struct.pack("<3f", *_normal(t)))
            for v in t:
                f.write(struct.pack("<3f", *v))
            f.write(struct.pack("<H", 0))


# ---------------------------------------------------------------------- CLI --


def main():
    p = argparse.ArgumentParser(
        description="Gera base de display em STL (paramétrica, sem dependências)."
    )
    p.add_argument("--diametro", type=float, default=85.0,
                   help="Diâmetro da base, em mm (padrão: 85)")
    p.add_argument("--diametro-topo", type=float, default=None,
                   help="Diâmetro do topo (padrão: 88%% da base, dando o cone)")
    p.add_argument("--altura", type=float, default=18.0,
                   help="Altura da base, em mm (padrão: 18)")
    p.add_argument("--furo", type=float, default=12.0,
                   help="Diâmetro MEDIDO da verga, em mm (padrão: 12)")
    p.add_argument("--folga", type=float, default=0.4,
                   help="Folga somada ao furo para encaixar, em mm (padrão: 0.4)")
    p.add_argument("--profundidade", type=float, default=12.0,
                   help="Profundidade do furo, em mm (padrão: 12)")
    p.add_argument("--segmentos", type=int, default=128,
                   help="Segmentos do círculo — mais = mais liso (padrão: 128)")
    p.add_argument("--saida", default="output/base_berimbau.stl",
                   help="Arquivo de saída")
    args = p.parse_args()

    diametro_topo = args.diametro_topo or args.diametro * 0.88
    diametro_furo = args.furo + args.folga

    tris = gerar_base(
        diametro_base=args.diametro,
        diametro_topo=diametro_topo,
        altura=args.altura,
        diametro_furo=diametro_furo,
        profundidade_furo=args.profundidade,
        segmentos=args.segmentos,
    )
    escrever_stl(tris, args.saida)

    print(f"\n  Gerado: {args.saida}")
    print(f"  {len(tris)} triângulos\n")
    print(f"  Base .......... {args.diametro:.1f} mm")
    print(f"  Topo .......... {diametro_topo:.1f} mm")
    print(f"  Altura ........ {args.altura:.1f} mm")
    print(f"  Furo .......... {diametro_furo:.1f} mm "
          f"(verga {args.furo:.1f} + folga {args.folga:.1f})")
    print(f"  Profundidade .. {args.profundidade:.1f} mm\n")
    print("  Fatiamento: sem suporte, 4 paredes, 40-60% de preenchimento.")
    print("  O peso da base é o que impede o berimbau de tombar.\n")


if __name__ == "__main__":
    main()
