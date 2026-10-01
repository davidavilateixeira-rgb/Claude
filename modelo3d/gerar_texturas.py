"""
Gera as texturas do modelo 3D do Laboratorio de P&D (placas e pisos).

Requisitos: Python 3 + Pillow + numpy
    pip install pillow numpy
    python gerar_texturas.py

Os arquivos PNG sao gravados em ./texturas e depois carregados pelo
gerar_modelo.py (script do Blender). Para trocar os textos das placas,
edite o dicionario PLACAS abaixo e rode este script novamente.
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
DIR_TEX = os.path.join(AQUI, "texturas")
DIR_FONTES = os.path.join(AQUI, "fontes")

LARANJA = (242, 122, 26, 255)
BRANCO = (245, 245, 242, 255)
PRETO_PLACA = (22, 23, 25, 255)

FONTE_BOLD = os.path.join(DIR_FONTES, "BarlowCondensed-Bold.ttf")
FONTE_SEMI = os.path.join(DIR_FONTES, "BarlowCondensed-SemiBold.ttf")
FONTE_MEDIA = os.path.join(DIR_FONTES, "BarlowCondensed-Medium.ttf")

SS = 2  # supersampling para bordas suaves


def fonte(caminho, tamanho):
    return ImageFont.truetype(caminho, int(tamanho))


# ---------------------------------------------------------------------------
# Icones (desenhados em laranja, estilo "linha" como nas placas da foto)
# ---------------------------------------------------------------------------
def icone_engrenagem(d, cx, cy, r, cor, dentes=10, furo=True):
    pts = []
    n = dentes * 4
    for i in range(n):
        a = 2 * math.pi * i / n
        fase = i % 4
        rr = r if fase in (1, 2) else r * 0.78
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=cor)
    if furo:
        rh = r * 0.52
        d.ellipse([cx - rh, cy - rh, cx + rh, cy + rh], fill=(0, 0, 0, 0))
        ri = r * 0.30
        w = max(2, int(r * 0.09))
        d.ellipse([cx - ri, cy - ri, cx + ri, cy + ri], outline=cor, width=w)


def icone_circuito(d, cx, cy, r, cor):
    """Cabeca com circuitos (automacao)."""
    w = max(2, int(r * 0.07))
    # contorno de perfil de cabeca
    d.arc([cx - r * 0.9, cy - r, cx + r * 0.9, cy + r * 0.8], 180, 360, fill=cor, width=w)
    d.line([cx - r * 0.9, cy - r * 0.1, cx - r * 0.9, cy + r * 0.5], fill=cor, width=w)
    d.line([cx - r * 0.9, cy + r * 0.5, cx - r * 0.55, cy + r * 0.95], fill=cor, width=w)
    d.line([cx + r * 0.9, cy - r * 0.1, cx + r * 0.75, cy + r * 0.25], fill=cor, width=w)
    d.line([cx + r * 0.75, cy + r * 0.25, cx + r * 0.95, cy + r * 0.45], fill=cor, width=w)
    d.line([cx + r * 0.95, cy + r * 0.45, cx + r * 0.7, cy + r * 0.6], fill=cor, width=w)
    d.line([cx + r * 0.7, cy + r * 0.6, cx + r * 0.7, cy + r * 0.95], fill=cor, width=w)
    # trilhas internas
    rng = random.Random(7)
    for k in range(6):
        y = cy - r * 0.55 + k * r * 0.22
        x0 = cx - r * 0.55 + rng.random() * r * 0.2
        x1 = cx + r * 0.2 + rng.random() * r * 0.35
        xm = (x0 + x1) / 2
        d.line([x0, y, xm, y, xm + r * 0.12, y + r * 0.1, x1, y + r * 0.1], fill=cor, width=max(2, w // 2))
        rn = r * 0.07
        d.ellipse([x0 - rn, y - rn, x0 + rn, y + rn], outline=cor, width=max(2, w // 2))
        d.ellipse([x1 - rn, y + r * 0.1 - rn, x1 + rn, y + r * 0.1 + rn], fill=cor)


def icone_lampada(d, cx, cy, r, cor):
    w = max(2, int(r * 0.08))
    rb = r * 0.55
    d.arc([cx - rb, cy - r * 0.75, cx + rb, cy + r * 0.35], 140, 400, fill=cor, width=w)
    d.line([cx - rb * 0.62, cy + r * 0.25, cx - rb * 0.45, cy + r * 0.55], fill=cor, width=w)
    d.line([cx + rb * 0.62, cy + r * 0.25, cx + rb * 0.45, cy + r * 0.55], fill=cor, width=w)
    for k in range(3):
        y = cy + r * (0.6 + 0.14 * k)
        d.line([cx - rb * 0.45, y, cx + rb * 0.45, y], fill=cor, width=w)
    # filamento
    d.line([cx - rb * 0.25, cy + r * 0.45, cx - rb * 0.25, cy - r * 0.05, cx, cy - r * 0.25,
            cx + rb * 0.25, cy - r * 0.05, cx + rb * 0.25, cy + r * 0.45], fill=cor, width=max(2, w // 2))
    # raios
    for ang in (-150, -120, -90, -60, -30):
        a = math.radians(ang)
        x0, y0 = cx + math.cos(a) * r * 0.78, cy - r * 0.2 + math.sin(a) * r * 0.78
        x1, y1 = cx + math.cos(a) * r * 1.0, cy - r * 0.2 + math.sin(a) * r * 1.0
        d.line([x0, y0, x1, y1], fill=cor, width=w)


def icone_reuniao(d, cx, cy, r, cor):
    w = max(2, int(r * 0.08))
    for dx, s in ((-0.62, 0.8), (0.0, 1.0), (0.62, 0.8)):
        hx = cx + dx * r
        hr = r * 0.17 * s
        hy = cy - r * 0.5
        d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], outline=cor, width=w)
        d.arc([hx - hr * 1.9, hy + hr * 1.2, hx + hr * 1.9, hy + hr * 4.6], 180, 360, fill=cor, width=w)
    # mesa
    d.rectangle([cx - r * 0.95, cy + r * 0.25, cx + r * 0.95, cy + r * 0.38], outline=cor, width=w)
    d.line([cx - r * 0.7, cy + r * 0.38, cx - r * 0.7, cy + r * 0.85], fill=cor, width=w)
    d.line([cx + r * 0.7, cy + r * 0.38, cx + r * 0.7, cy + r * 0.85], fill=cor, width=w)
    # notebook
    d.rectangle([cx - r * 0.2, cy + r * 0.05, cx + r * 0.2, cy + r * 0.25], outline=cor, width=max(2, w // 2))


def icone_duas_engrenagens(d, cx, cy, r, cor):
    icone_engrenagem(d, cx - r * 0.25, cy - r * 0.3, r * 0.62, cor, dentes=9)
    icone_engrenagem(d, cx + r * 0.42, cy + r * 0.42, r * 0.45, cor, dentes=8)


ICONES = {
    "engrenagem": icone_engrenagem,
    "circuito": icone_circuito,
    "lampada": icone_lampada,
    "reuniao": icone_reuniao,
}

# ---------------------------------------------------------------------------
# Placas (texto editavel)
# largura/altura em pixels: proporcional ao tamanho real definido no modelo
# ---------------------------------------------------------------------------
PLACAS = {
    "placa_mecanica": dict(tam=(2048, 416), icone="engrenagem",
                           linhas=[("ENGENHARIA", FONTE_SEMI, 0.36), ("MECÂNICA", FONTE_BOLD, 0.50)]),
    "placa_automacao": dict(tam=(2048, 424), icone="circuito",
                            linhas=[("ENGENHARIA DE", FONTE_SEMI, 0.34), ("AUTOMAÇÃO", FONTE_BOLD, 0.48)]),
    "placa_projetos": dict(tam=(1024, 340), icone="lampada",
                           linhas=[("SALA DE", FONTE_SEMI, 0.34), ("PROJETOS", FONTE_BOLD, 0.40)]),
    "placa_reunioes": dict(tam=(1024, 300), icone="reuniao",
                           linhas=[("SALA DE", FONTE_SEMI, 0.36), ("REUNIÕES", FONTE_BOLD, 0.42)]),
}

PLACA_PRINCIPAL = dict(
    arquivo="placa_laboratorio",
    tam=(2048, 838),
    titulo=["LABORATÓRIO", "DE ENGENHARIA"],
    lema="INOVAÇÃO  •  PRÁTICA  •  SOLUÇÕES",
)


def placa_parede(nome, tam, icone, linhas):
    W, H = tam[0] * SS, tam[1] * SS
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = H * 0.36
    cx, cy = H * 0.5, H * 0.5
    ICONES[icone](d, cx, cy, r, LARANJA)
    x = H * 0.5 + r + H * 0.18
    # posiciona as linhas pela caixa real do texto (inclui acentos: Â, Ã, Õ)
    blocos = []
    for texto, f, h in linhas:
        fn = fonte(f, h * H * 1.25)
        x0, topo, x1, base = fn.getbbox(texto, anchor="ls")
        blocos.append((texto, fn, topo, base))
    espaco = H * 0.05
    total = sum(b - t for _, _, t, b in blocos) + espaco * (len(blocos) - 1)
    y = (H - total) / 2
    for texto, fn, topo, base in blocos:
        d.text((x, y - topo), texto, font=fn, fill=BRANCO, anchor="ls")
        y += (base - topo) + espaco
    im = im.resize(tam, Image.LANCZOS)
    im.save(os.path.join(DIR_TEX, nome + ".png"))


def placa_principal():
    W, H = PLACA_PRINCIPAL["tam"][0] * SS, PLACA_PRINCIPAL["tam"][1] * SS
    im = Image.new("RGBA", (W, H), PRETO_PLACA)
    d = ImageDraw.Draw(im)
    m = int(H * 0.035)
    d.rectangle([m, m, W - m, H - m], outline=(70, 70, 72, 255), width=max(2, SS * 3))
    icone_duas_engrenagens(d, W * 0.12, H * 0.33, H * 0.22, LARANJA)
    fn = fonte(FONTE_BOLD, H * 0.25)
    d.text((W * 0.22, H * 0.36), PLACA_PRINCIPAL["titulo"][0], font=fn, fill=BRANCO, anchor="ls")
    d.text((W * 0.22, H * 0.62), PLACA_PRINCIPAL["titulo"][1], font=fn, fill=BRANCO, anchor="ls")
    d.rectangle([W * 0.07, H * 0.71, W * 0.93, H * 0.715 + SS * 3], fill=LARANJA)
    fn2 = fonte(FONTE_SEMI, H * 0.12)
    d.text((W * 0.5, H * 0.86), PLACA_PRINCIPAL["lema"], font=fn2, fill=LARANJA, anchor="ms")
    im = im.resize(PLACA_PRINCIPAL["tam"], Image.LANCZOS)
    im.save(os.path.join(DIR_TEX, PLACA_PRINCIPAL["arquivo"] + ".png"))


def tela_cad():
    """Imagem de tela (CAD) usada em monitores e TVs."""
    W, H = 1024, 576
    im = Image.new("RGB", (W, H), (18, 24, 34))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 34], fill=(40, 48, 60))
    d.rectangle([0, 34, 120, H], fill=(30, 37, 48))
    for i in range(10):
        d.rectangle([20, 60 + i * 44, 100, 84 + i * 44], fill=(60, 72, 90))
    for gx in range(140, W, 40):
        d.line([gx, 34, gx, H], fill=(26, 34, 46))
    for gy in range(34, H, 40):
        d.line([120, gy, W, gy], fill=(26, 34, 46))
    tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dt = ImageDraw.Draw(tmp)
    icone_engrenagem(dt, 520, 300, 170, (90, 200, 255, 255), dentes=12)
    icone_engrenagem(dt, 780, 200, 100, (242, 122, 26, 255), dentes=9)
    im.paste(tmp, (0, 0), tmp)
    im.save(os.path.join(DIR_TEX, "tela_cad.png"), optimize=True)


# ---------------------------------------------------------------------------
# Texturas de piso (repetiveis / "seamless")
# ---------------------------------------------------------------------------
def ruido(n, escala, seed):
    """Ruido suave e repetivel (filtrado no dominio da frequencia)."""
    rng = np.random.default_rng(seed)
    w = rng.standard_normal((n, n))
    f = np.fft.fftfreq(n)
    fx, fy = np.meshgrid(f, f)
    g = np.exp(-(fx ** 2 + fy ** 2) * (escala ** 2) * 2.0)
    r = np.real(np.fft.ifft2(np.fft.fft2(w) * g))
    r -= r.min()
    r /= r.max() + 1e-9
    return r


def ruido_fractal(n, seed, oitavas=((64, 0.5), (16, 0.3), (4, 0.2))):
    acc = np.zeros((n, n))
    for i, (esc, peso) in enumerate(oitavas):
        acc += ruido(n, esc, seed + i) * peso
    return acc


def mistura(c0, c1, t):
    c0 = np.array(c0, float)
    c1 = np.array(c1, float)
    return c0[None, None, :] * (1 - t[..., None]) + c1[None, None, :] * t[..., None]


def desenha_envolto(n, func):
    """Chama func(dx, dy) com deslocamentos para o desenho repetir nas bordas."""
    for dx in (-n, 0, n):
        for dy in (-n, 0, n):
            func(dx, dy)


def tex_grama():
    n = 1024
    t = ruido_fractal(n, 1)
    base = mistura((70, 104, 38), (118, 146, 56), t)
    fino = ruido(n, 1.2, 9)
    base *= (0.82 + 0.3 * fino)[..., None]
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    rng = random.Random(3)
    for _ in range(26000):
        x, y = rng.random() * n, rng.random() * n
        L = 3 + rng.random() * 7
        a = rng.random() * math.pi
        c = rng.choice([(96, 132, 46), (60, 92, 32), (128, 156, 64), (84, 120, 40)])
        def f(dx, dy, x=x, y=y, L=L, a=a, c=c):
            d.line([x + dx, y + dy, x + dx + math.cos(a) * L, y + dy + math.sin(a) * L], fill=c, width=1)
        if x < 12 or y < 12 or x > n - 12 or y > n - 12:
            desenha_envolto(n, f)
        else:
            f(0, 0)
    im.save(os.path.join(DIR_TEX, "grama.jpg"), quality=88)


def tex_brita():
    n = 1024
    t = ruido_fractal(n, 20)
    base = mistura((122, 109, 90), (164, 150, 128), t)
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    rng = random.Random(5)
    for _ in range(16000):
        x, y = rng.random() * n, rng.random() * n
        rx, ry = 2 + rng.random() * 6, 2 + rng.random() * 5
        g = rng.randint(120, 215)
        tint = rng.choice([(-4, -8, -14), (8, 0, -12), (-10, -12, -14), (12, 4, -8)])
        c = tuple(max(0, min(255, g + k)) for k in tint)
        sombra = tuple(int(v * 0.55) for v in c)
        def f(dx, dy, x=x, y=y, rx=rx, ry=ry, c=c, s=sombra):
            d.ellipse([x + dx - rx + 1, y + dy - ry + 1.5, x + dx + rx + 1, y + dy + ry + 1.5], fill=s)
            d.ellipse([x + dx - rx, y + dy - ry, x + dx + rx, y + dy + ry], fill=c)
        if x < 10 or y < 10 or x > n - 10 or y > n - 10:
            desenha_envolto(n, f)
        else:
            f(0, 0)
    im.save(os.path.join(DIR_TEX, "brita.jpg"), quality=88)


def tex_paralelepipedo():
    n = 1024
    im = Image.new("RGB", (n, n), (58, 56, 54))
    d = ImageDraw.Draw(im)
    rng = random.Random(11)
    linhas = 16
    h = n / linhas
    for i in range(linhas):
        y0 = i * h
        x = (rng.random() * 40) if i % 2 else 0
        larg_base = n / 10
        xs = [0]
        while xs[-1] < n - larg_base * 0.6:
            xs.append(xs[-1] + larg_base * (0.8 + rng.random() * 0.4))
        xs[-1] = n
        for a, b in zip(xs[:-1], xs[1:]):
            g = rng.randint(105, 160)
            c = (g, g - 2, g - 6)
            off = (i % 2) * larg_base * 0.5
            for dx in (-n, 0):
                x0, x1 = a + off + dx + 3, b + off + dx - 3
                d.rounded_rectangle([x0, y0 + 3, x1, y0 + h - 3], radius=8, fill=c)
                d.line([x0 + 4, y0 + 5, x1 - 4, y0 + 5], fill=tuple(min(255, v + 25) for v in c), width=2)
    arr = np.array(im).astype(float)
    arr *= (0.85 + 0.25 * ruido(n, 3, 4))[..., None]
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(os.path.join(DIR_TEX, "paralelepipedo.jpg"), quality=88)


def tex_concreto():
    n = 1024
    t = ruido_fractal(n, 30, ((128, 0.4), (32, 0.3), (2, 0.3)))
    base = mistura((150, 148, 142), (196, 193, 186), t)
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    # juntas de dilatacao a cada 1,5 m (tile = 3 m)
    for k in (0, n // 2):
        d.line([k, 0, k, n], fill=(120, 118, 112), width=3)
        d.line([0, k, n, k], fill=(120, 118, 112), width=3)
    im.save(os.path.join(DIR_TEX, "concreto.jpg"), quality=88)


def tex_madeira():
    n = 1024
    im = Image.new("RGB", (n, n))
    arr = np.zeros((n, n, 3))
    rng = np.random.default_rng(2)
    larg = n // 11  # tabuas de ~18 cm (tile = 2 m)
    veio = ruido(n, 1.5, 33)
    for i in range(0, n, larg):
        cor = np.array([196, 154, 106]) * (0.85 + rng.random() * 0.25)
        faixa = np.linspace(0, 6 * math.pi, n)
        listras = 0.5 + 0.5 * np.sin(faixa[None, :] * (1 + rng.random()) + veio[i:i + larg, :] * 8)
        arr[i:i + larg, :, :] = cor[None, None, :] * (0.88 + 0.12 * listras[..., None])
        arr[i:i + 2, :, :] *= 0.6
        corte = rng.integers(0, n)
        arr[i:i + larg, corte:corte + 2, :] *= 0.6
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(os.path.join(DIR_TEX, "madeira_piso.jpg"), quality=88)


def main():
    os.makedirs(DIR_TEX, exist_ok=True)
    for nome, p in PLACAS.items():
        placa_parede(nome, p["tam"], p["icone"], p["linhas"])
    placa_principal()
    tela_cad()
    tex_grama()
    tex_brita()
    tex_paralelepipedo()
    tex_concreto()
    tex_madeira()
    print("Texturas geradas em", DIR_TEX)


if __name__ == "__main__":
    main()
