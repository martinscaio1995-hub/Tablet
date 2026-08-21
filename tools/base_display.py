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


def _retangulo(largura: float, altura: float, z: float, segmentos: int) -> list[tuple]:
    """Contorno de um retângulo amostrado em `segmentos` pontos igualmente
    espaçados ao longo do perímetro, no mesmo sentido do círculo.

    Manter a mesma contagem de pontos do contorno externo é o que permite
    reaproveitar as funções de coroa e parede sem tratar caso especial.
    """
    w, h = largura / 2, altura / 2
    cantos = [(w, -h), (w, h), (-w, h), (-w, -h)]
    lados = [(cantos[i], cantos[(i + 1) % 4]) for i in range(4)]
    comprimentos = [
        math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in lados
    ]
    perimetro = sum(comprimentos)

    pontos = []
    for i in range(segmentos):
        d = perimetro * i / segmentos
        for (a, b), comp in zip(lados, comprimentos):
            if d <= comp or (a, b) == lados[-1]:
                t = d / comp
                pontos.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, z))
                break
            d -= comp
    return pontos


def _tampa(pontos: list[tuple], z: float, para_cima: bool) -> list[tuple]:
    """Disco cheio, em leque a partir do centro."""
    centro = (0.0, 0.0, z)
    n = len(pontos)
    if para_cima:
        return [(centro, pontos[i], pontos[(i + 1) % n]) for i in range(n)]
    return [(centro, pontos[(i + 1) % n], pontos[i]) for i in range(n)]


def _coroa(externo: list[tuple], interno: list[tuple], para_cima: bool) -> list[tuple]:
    """Anel plano entre dois círculos concêntricos (face com furo no meio)."""
    tris = []
    n = len(externo)
    for i in range(n):
        j = (i + 1) % n
        if para_cima:
            tris.append((externo[i], externo[j], interno[j]))
            tris.append((externo[i], interno[j], interno[i]))
        else:
            tris.append((externo[i], interno[j], externo[j]))
            tris.append((externo[i], interno[i], interno[j]))
    return tris


def _parede(baixo: list[tuple], cima: list[tuple], para_fora: bool) -> list[tuple]:
    """Superfície lateral entre dois círculos em alturas diferentes."""
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


def gerar_secao(
    z0: float,
    z1: float,
    raio_em,
    contorno_furo,
    z_furo: float,
    segmentos: int,
) -> list[tuple]:
    """Gera uma fatia horizontal da base, entre z0 e z1, já descontando o
    furo onde ele existir.

    Cada fatia sai como sólido fechado independente — é isso que permite
    imprimir cada uma em uma cor e o fatiador aceitar sem reparo.
    """
    ext_baixo = _circulo(raio_em(z0), z0, segmentos)
    ext_cima = _circulo(raio_em(z1), z1, segmentos)

    # O furo ocupa de z_furo até o topo da peça. Nesta fatia ele aparece
    # só se o topo dela estiver acima do início do furo.
    tem_furo = z1 > z_furo
    furo_atravessa_baixo = z0 >= z_furo

    tris = list(_parede(ext_baixo, ext_cima, para_fora=True))

    if not tem_furo:
        tris += _tampa(ext_baixo, z0, para_cima=False)
        tris += _tampa(ext_cima, z1, para_cima=True)
        return tris

    z_inicio_furo = max(z0, z_furo)
    furo_lo = contorno_furo(z_inicio_furo)
    furo_hi = contorno_furo(z1)

    # Face de baixo: vira anel se o furo já a atravessa, senão é disco cheio.
    if furo_atravessa_baixo:
        tris += _coroa(ext_baixo, contorno_furo(z0), para_cima=False)
    else:
        tris += _tampa(ext_baixo, z0, para_cima=False)
        # Fundo do furo cai dentro desta fatia.
        tris += _tampa(furo_lo, z_inicio_furo, para_cima=True)

    tris += _parede(furo_lo, furo_hi, para_fora=False)
    tris += _coroa(ext_cima, furo_hi, para_cima=True)
    return tris


def gerar_base(
    diametro_base: float,
    diametro_topo: float,
    altura: float,
    diametro_furo: float,
    profundidade_furo: float,
    segmentos: int,
    faixas: list[float] | None = None,
    furo_retangular: tuple[float, float] | None = None,
) -> list[list[tuple]]:
    """Monta a base como tronco de cone com furo cego central.

    `faixas` são alturas (mm) onde cortar a peça em bandas horizontais —
    uma por cor. Sem faixas, retorna uma peça única.

    Retorna uma lista de malhas, de baixo para cima.
    """
    r_base = diametro_base / 2
    r_topo = diametro_topo / 2
    r_furo = diametro_furo / 2
    z_furo = altura - profundidade_furo

    if furo_retangular:
        largura, profund = furo_retangular
        r_furo = math.hypot(largura, profund) / 2  # meia-diagonal, para as checagens
        def contorno_furo(z):
            return _retangulo(largura, profund, z, segmentos)
    else:
        def contorno_furo(z):
            return _circulo(r_furo, z, segmentos)

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

    cortes = sorted({round(z, 4) for z in (faixas or []) if 0 < z < altura})
    limites = [0.0, *cortes, altura]

    def raio_em(z: float) -> float:
        return r_base + (r_topo - r_base) * (z / altura)

    return [
        gerar_secao(z0, z1, raio_em, contorno_furo, z_furo, segmentos)
        for z0, z1 in zip(limites, limites[1:])
    ]


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


# Bandas do preset --berimbau: verde e amarelo do Brasil na barra de baixo,
# corpo em tom de madeira, como a verga e a cabaça natural.
PRESET_BERIMBAU = {
    "faixas": [3.0, 6.0],
    "nomes": ["verde", "amarelo", "madeira"],
}


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
    p.add_argument("--furo-retangular", default="",
                   help="Encaixe retangular em vez de redondo: LARGURAxALTURA em mm "
                        "medidas na peça (ex: 4.63x4.0). A folga é somada aos dois "
                        "lados. Use quando a ponta não for cilíndrica — furo redondo "
                        "deixaria a peça girar.")
    p.add_argument("--berimbau", action="store_true",
                   help="Preset multicolor: faixa verde, faixa amarela e corpo madeira")
    p.add_argument("--faixas", default="",
                   help="Alturas de corte em mm, separadas por vírgula (ex: 3,6). "
                        "Cada banda vira um STL, para imprimir em cor diferente.")
    p.add_argument("--saida", default="output/base_berimbau.stl",
                   help="Arquivo de saída (multicolor gera um por banda)")
    args = p.parse_args()

    diametro_topo = args.diametro_topo or args.diametro * 0.88
    diametro_furo = args.furo + args.folga

    furo_ret = None
    if args.furo_retangular:
        try:
            larg, alt = (float(v) for v in args.furo_retangular.lower().split("x"))
        except ValueError:
            p.error("--furo-retangular espera LARGURAxALTURA, ex: 4.63x4.0")
        furo_ret = (larg + args.folga, alt + args.folga)

    if args.berimbau:
        faixas = PRESET_BERIMBAU["faixas"]
        nomes = PRESET_BERIMBAU["nomes"]
    elif args.faixas:
        faixas = [float(z) for z in args.faixas.split(",")]
        nomes = None
    else:
        faixas, nomes = [], None

    partes = gerar_base(
        diametro_base=args.diametro,
        diametro_topo=diametro_topo,
        altura=args.altura,
        diametro_furo=diametro_furo,
        profundidade_furo=args.profundidade,
        segmentos=args.segmentos,
        faixas=faixas,
        furo_retangular=furo_ret,
    )

    if nomes is None:
        nomes = [f"parte{i + 1}" for i in range(len(partes))]
    elif len(nomes) != len(partes):
        nomes = [f"parte{i + 1}" for i in range(len(partes))]

    base_nome = args.saida.rsplit(".stl", 1)[0]
    limites = [0.0, *sorted(faixas), args.altura]

    print()
    if len(partes) == 1:
        escrever_stl(partes[0], args.saida)
        print(f"  Gerado: {args.saida} ({len(partes[0])} triângulos)")
    else:
        for i, (malha, nome) in enumerate(zip(partes, nomes), start=1):
            caminho = f"{base_nome}_{i}_{nome}.stl"
            escrever_stl(malha, caminho)
            print(f"  {caminho}")
            print(f"      z {limites[i - 1]:.1f} → {limites[i]:.1f} mm"
                  f"   ({len(malha)} triângulos)")

    print(f"\n  Base .......... {args.diametro:.1f} mm")
    print(f"  Topo .......... {diametro_topo:.1f} mm")
    print(f"  Altura ........ {args.altura:.1f} mm")
    if furo_ret:
        print(f"  Encaixe ....... {furo_ret[0]:.2f} x {furo_ret[1]:.2f} mm "
              f"retangular (peça {args.furo_retangular} + folga {args.folga:.1f})")
    else:
        print(f"  Furo .......... {diametro_furo:.1f} mm "
              f"(verga {args.furo:.1f} + folga {args.folga:.1f})")
    print(f"  Profundidade .. {args.profundidade:.1f} mm\n")
    print("  Fatiamento: sem suporte, 4 paredes, 40-60% de preenchimento.")
    print("  O peso da base é o que impede o berimbau de tombar.\n")
    if len(partes) > 1:
        print("  MULTICOLOR (AMS) — as bandas já saem na posição certa:")
        print("  1. Selecione os arquivos juntos ao importar no Bambu Studio.")
        print("  2. Responda SIM em 'carregar como objeto único' — é isso que")
        print("     mantém o alinhamento entre as bandas.")
        print("  3. Na aba de objetos, atribua um filamento do AMS a cada parte.\n")


if __name__ == "__main__":
    main()
