"""
Laboratorio de Engenharia (P&D) em conteineres maritimos - modelo 3D parametrico.

Gera a cena completa no Blender (conteineres corrugados, pergolado metalico,
escada externa, esquadrias, placas, interiores, paisagismo e vegetacao),
organizada em colecoes e com todas as medidas em metros.

Como usar
---------
1) Dentro do Blender (4.x): aba "Scripting" > abrir este arquivo > "Run Script".
   A cena e reconstruida do zero (nada e exportado).
2) Linha de comando (gera e exporta .blend/.glb/.fbx/.obj/.dae):
       blender --background --python gerar_modelo.py -- [--render]
   ou, com o modulo bpy instalado (pip install bpy==4.2.0):
       python gerar_modelo.py [--render]

Para editar: altere as constantes da secao "PARAMETROS" (posicoes dos blocos,
aberturas, mobiliario...) e rode novamente. Os textos das placas ficam em
gerar_texturas.py. Eixos (Blender): X = ao longo da fachada, Y = profundidade
(fachada principal em Y=0, fundos para +Y), Z = altura.
"""
import math
import os
import random
import sys

import bpy  # noqa: E402  (bpy precisa vir antes de bmesh no modulo pip)
import bmesh
from mathutils import Vector

# ===========================================================================
# PARAMETROS
# ===========================================================================
try:
    AQUI = os.path.dirname(os.path.abspath(__file__))
except NameError:
    AQUI = os.getcwd()
if not os.path.isdir(os.path.join(AQUI, "texturas")):
    AQUI = os.getcwd()
DIR_TEX = os.path.join(AQUI, "texturas")
DIR_SAIDA = os.path.join(AQUI, "saida")
NOME_ARQ = "laboratorio_pd"

# Conteiner High Cube (ISO): comprimentos 20', 30' e 40'
L20, L30, L40 = 6.058, 9.125, 12.192
CW, CH = 2.438, 2.896          # largura e altura externas
BASE = 0.05                     # cota do piso externo (calcada) / apoio dos conteineres
PISO_INT = 0.13                 # espessura do piso interno do conteiner

X_MEC = 0.0                     # Bloco Engenharia Mecanica
X_PERG0, X_PERG1 = 12.55, 20.40  # pergolado (vao entre pilares)
X_AUT = 20.40                   # Bloco Engenharia de Automacao
X_SALAS = 35.20                 # Bloco Sala de Projetos / Sala de Reunioes
ESCADA_X0 = 33.00               # inicio da escada externa

PLACA_XY = (26.5, -19.0)        # placa "Laboratorio de Engenharia" no gramado
MEIO_FIO_Y0, MEIO_FIO_INCL = -5.5, 0.518   # meio-fio diagonal gramado/estacionamento

SEMENTE = 42

# ===========================================================================
# MATERIAIS
# ===========================================================================
MATS = {
    # nome: cor (sRGB hex), rugosidade, metalico, extras
    "Conteiner_Preto": dict(cor="#1c1e21", r=0.5, m=0.45),
    "Aco_Preto": dict(cor="#121314", r=0.4, m=0.7),
    "Aco_Galvanizado": dict(cor="#8d9095", r=0.35, m=0.85),
    "Vidro": dict(cor="#a9c0cc", r=0.03, m=0.0, alpha=0.28),
    "Laranja": dict(cor="#f07a1a", r=0.42, m=0.1),
    "Interior_Branco": dict(cor="#ebe7df", r=0.85, m=0.0),
    "Teto_Interior": dict(cor="#f3f1ec", r=0.9, m=0.0),
    "Luz_Teto": dict(cor="#fff3dc", r=0.5, m=0.0, emis=8.0),
    "Luz_Externa": dict(cor="#ffd7a0", r=0.5, m=0.0, emis=6.0),
    "Piso_Madeira": dict(tex="madeira_piso.jpg", tile=2.0, r=0.45, m=0.0),
    "Madeira_Mesa": dict(cor="#c89b64", r=0.55, m=0.0),
    "Concreto": dict(tex="concreto.jpg", tile=3.0, r=0.85, m=0.0),
    "Concreto_Meio_Fio": dict(cor="#bdb8ad", r=0.85, m=0.0),
    "Grama": dict(tex="grama.jpg", tile=4.0, r=0.95, m=0.0),
    "Grama_Campo": dict(tex="grama.jpg", tile=7.0, r=0.95, m=0.0),
    "Brita": dict(tex="brita.jpg", tile=3.0, r=0.95, m=0.0),
    "Paralelepipedo": dict(tex="paralelepipedo.jpg", tile=2.2, r=0.9, m=0.0),
    "Folhagem": dict(cor="#3c672a", r=0.8, m=0.0),
    "Folhagem_Clara": dict(cor="#5e8f36", r=0.8, m=0.0),
    "Folhagem_Escura": dict(cor="#26431d", r=0.85, m=0.0),
    "Pinheiro": dict(cor="#223a1d", r=0.85, m=0.0),
    "Tronco": dict(cor="#4b392a", r=0.9, m=0.0),
    "Vaso": dict(cor="#202122", r=0.55, m=0.1),
    "Terra": dict(cor="#3b2e22", r=1.0, m=0.0),
    "Tela_CAD": dict(tex="tela_cad.png", tile=1.0, r=0.2, m=0.0, emis_tex=1.6),
    "Tela_Desligada": dict(cor="#0a0c0f", r=0.12, m=0.0),
    "Plastico_Preto": dict(cor="#1f2022", r=0.5, m=0.0),
    "Estofado": dict(cor="#2b2e33", r=0.9, m=0.0),
    "Cinza_Maquina": dict(cor="#56626b", r=0.45, m=0.4),
    "Quadro_Eletrico": dict(cor="#c8cbcd", r=0.45, m=0.3),
    "Condensadora": dict(cor="#e1e1dc", r=0.5, m=0.1),
    "Quadro_Branco": dict(cor="#f7f7f5", r=0.15, m=0.0),
    "Telha_Metalica": dict(cor="#25272a", r=0.45, m=0.6),
    "Placa_Fundo": dict(cor="#161719", r=0.6, m=0.1),
    "Placa_Mecanica": dict(tex="placa_mecanica.png", clip=True, r=0.6, m=0.0),
    "Placa_Automacao": dict(tex="placa_automacao.png", clip=True, r=0.6, m=0.0),
    "Placa_Projetos": dict(tex="placa_projetos.png", clip=True, r=0.6, m=0.0),
    "Placa_Reunioes": dict(tex="placa_reunioes.png", clip=True, r=0.6, m=0.0),
    "Placa_Laboratorio": dict(tex="placa_laboratorio.png", r=0.6, m=0.0),
    "Livros_Caixas": dict(cor="#8a6a48", r=0.8, m=0.0),
    "Azul_Detalhe": dict(cor="#2f5f8f", r=0.5, m=0.0),
}


def srgb_linear(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


_cache_mat = {}


def material(nome):
    if nome in _cache_mat:
        return _cache_mat[nome]
    p = MATS[nome]
    mat = bpy.data.materials.new(nome)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = p.get("r", 0.5)
    bsdf.inputs["Metallic"].default_value = p.get("m", 0.0)
    if "cor" in p:
        bsdf.inputs["Base Color"].default_value = srgb_linear(p["cor"]) + [1.0]
        mat.diffuse_color = srgb_linear(p["cor"]) + [1.0]
    if "tex" in p:
        img = bpy.data.images.load(os.path.join(DIR_TEX, p["tex"]), check_existing=True)
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = img
        tn.location = (-600, 200)
        # textura ligada direto na cor base (assim OBJ/FBX/DAE/glTF levam a imagem junto)
        nt.links.new(tn.outputs["Color"], bsdf.inputs["Base Color"])
        if p.get("clip"):
            arred = nt.nodes.new("ShaderNodeMath")
            arred.operation = "ROUND"
            nt.links.new(tn.outputs["Alpha"], arred.inputs[0])
            nt.links.new(arred.outputs[0], bsdf.inputs["Alpha"])
            mat.blend_method = "CLIP"
        if "emis_tex" in p:
            nt.links.new(tn.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = p["emis_tex"]
    if "emis" in p:
        bsdf.inputs["Emission Color"].default_value = srgb_linear(p["cor"]) + [1.0]
        bsdf.inputs["Emission Strength"].default_value = p["emis"]
    if "alpha" in p:
        bsdf.inputs["Alpha"].default_value = p["alpha"]
        mat.blend_method = "BLEND"
        mat.use_backface_culling = False
        try:
            mat.surface_render_method = "BLENDED"
        except AttributeError:
            pass
    _cache_mat[nome] = mat
    return mat


# ===========================================================================
# CONSTRUTOR DE MALHAS (geometria pura; 1 objeto pode ter varios materiais)
# ===========================================================================
def V(*a):
    return Vector(a if len(a) == 3 else a[0])


def normal_newell(pts):
    n = Vector((0, 0, 0))
    for i, p in enumerate(pts):
        q = pts[(i + 1) % len(pts)]
        n.x += (p.y - q.y) * (p.z + q.z)
        n.y += (p.z - q.z) * (p.x + q.x)
        n.z += (p.x - q.x) * (p.y + q.y)
    return n.normalized() if n.length > 1e-12 else n


class Malha:
    def __init__(self, mat="Conteiner_Preto"):
        self.v, self.f, self.uv, self.uvw, self.sm, self.mt = [], [], [], [], [], []
        self.mat = mat

    # -- face basica ------------------------------------------------------
    def face(self, pts, dica=None, uv=None, liso=False, mat=None):
        pts = [Vector(p) for p in pts]
        n = normal_newell(pts)
        if dica is not None and n.dot(Vector(dica)) < 0:
            pts.reverse()
            n = -n
            if uv:
                uv = uv[::-1]
        mundo = uv is None
        if mundo:
            ax = max(range(3), key=lambda i: abs(n[i]))
            if ax == 2:
                uv = [(p.x, p.y) for p in pts]
            elif ax == 0:
                uv = [(p.y, p.z) for p in pts]
            else:
                uv = [(p.x, p.z) for p in pts]
        i = len(self.v)
        self.v.extend(pts)
        self.f.append(tuple(range(i, i + len(pts))))
        self.uv.append(uv)
        self.uvw.append(mundo)
        self.sm.append(liso)
        self.mt.append(mat or self.mat)

    def juntar(self, outra):
        k = len(self.v)
        self.v.extend(outra.v)
        self.f.extend(tuple(i + k for i in f) for f in outra.f)
        self.uv.extend(outra.uv)
        self.uvw.extend(outra.uvw)
        self.sm.extend(outra.sm)
        self.mt.extend(outra.mt)

    def transformar(self, rot_graus=0.0, desloc=(0, 0, 0)):
        c, s = math.cos(math.radians(rot_graus)), math.sin(math.radians(rot_graus))
        d = Vector(desloc)
        self.v = [Vector((p.x * c - p.y * s, p.x * s + p.y * c, p.z)) + d for p in self.v]
        return self

    # -- primitivas ---------------------------------------------------------
    def caixa(self, a, b, mat=None):
        x0, x1 = sorted((a[0], b[0]))
        y0, y1 = sorted((a[1], b[1]))
        z0, z1 = sorted((a[2], b[2]))
        P = lambda x, y, z: (x, y, z)
        self.face([P(x0, y0, z0), P(x0, y1, z0), P(x1, y1, z0), P(x1, y0, z0)], (0, 0, -1), mat=mat)
        self.face([P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)], (0, 0, 1), mat=mat)
        self.face([P(x0, y0, z0), P(x1, y0, z0), P(x1, y0, z1), P(x0, y0, z1)], (0, -1, 0), mat=mat)
        self.face([P(x0, y1, z0), P(x0, y1, z1), P(x1, y1, z1), P(x1, y1, z0)], (0, 1, 0), mat=mat)
        self.face([P(x0, y0, z0), P(x0, y0, z1), P(x0, y1, z1), P(x0, y1, z0)], (-1, 0, 0), mat=mat)
        self.face([P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1), P(x1, y0, z1)], (1, 0, 0), mat=mat)

    def paralelepipedo(self, o, a, b, c, mat=None):
        o, a, b, c = V(o), V(a), V(b), V(c)
        cen = o + (a + b + c) / 2
        quads = [(o, o + a, o + a + b, o + b), (o + c, o + a + c, o + a + b + c, o + b + c),
                 (o, o + a, o + a + c, o + c), (o + b, o + a + b, o + a + b + c, o + b + c),
                 (o, o + b, o + b + c, o + c), (o + a, o + a + b, o + a + b + c, o + a + c)]
        for q in quads:
            fc = sum(q, Vector()) / 4
            self.face(q, fc - cen, mat=mat)

    def barra(self, p0, p1, w, h=None, mat=None):
        """Perfil de secao retangular entre dois pontos (tubos, corrimaos, longarinas)."""
        p0, p1 = V(p0), V(p1)
        h = h or w
        d = p1 - p0
        e1 = d.normalized()
        ref = Vector((0, 0, 1)) if abs(e1.z) < 0.9 else Vector((1, 0, 0))
        e2 = e1.cross(ref).normalized()
        e3 = e1.cross(e2).normalized()
        o = p0 - e2 * (w / 2) - e3 * (h / 2)
        self.paralelepipedo(o, d, e2 * w, e3 * h, mat=mat)

    def cilindro(self, base, r0, r1, h, seg=16, tampas=True, mat=None, eixo=(0, 0, 1)):
        base = V(base)
        ez = Vector(eixo).normalized()
        ref = Vector((1, 0, 0)) if abs(ez.x) < 0.9 else Vector((0, 1, 0))
        ex = ez.cross(ref).normalized()
        ey = ez.cross(ex)
        topo = base + ez * h
        ang = [2 * math.pi * i / seg for i in range(seg)]
        anel0 = [base + (ex * math.cos(a) + ey * math.sin(a)) * r0 for a in ang]
        anel1 = [topo + (ex * math.cos(a) + ey * math.sin(a)) * r1 for a in ang]
        per = 2 * math.pi * max(r0, r1)
        for i in range(seg):
            j = (i + 1) % seg
            meio = (anel0[i] + anel0[j] + anel1[i] + anel1[j]) / 4
            dica = meio - (base + topo) / 2
            dica -= ez * dica.dot(ez)
            uv = [(per * i / seg, 0), (per * (i + 1) / seg, 0), (per * (i + 1) / seg, h), (per * i / seg, h)]
            if r1 <= 1e-6:
                self.face([anel0[i], anel0[j], topo], dica, liso=True, mat=mat)
            else:
                self.face([anel0[i], anel0[j], anel1[j], anel1[i]], dica, uv=uv, liso=True, mat=mat)
        if tampas:
            self.face(anel0, -ez, mat=mat)
            if r1 > 1e-6:
                self.face(anel1, ez, mat=mat)

    def esfera(self, c, r, rng=None, irreg=0.0, esc=(1, 1, 1), sub=1, mat=None):
        """Icosfera low-poly (copas de arvores, arbustos)."""
        t = (1 + 5 ** 0.5) / 2
        vs = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
              (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
        vs = [Vector(v).normalized() for v in vs]
        fs = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
              (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5),
              (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
        for _ in range(sub):
            meio = {}
            novas = []
            for a, b, cc in fs:
                ids = []
                for p, q in ((a, b), (b, cc), (cc, a)):
                    k = (min(p, q), max(p, q))
                    if k not in meio:
                        vs.append(((vs[p] + vs[q]) / 2).normalized())
                        meio[k] = len(vs) - 1
                    ids.append(meio[k])
                novas += [(a, ids[0], ids[2]), (b, ids[1], ids[0]), (cc, ids[2], ids[1]), tuple(ids)]
            fs = novas
        c = V(c)
        esc = Vector(esc)
        pts = []
        for v in vs:
            k = 1 + (rng.uniform(-irreg, irreg) if rng else 0)
            pts.append(c + Vector((v.x * esc.x, v.y * esc.y, v.z * esc.z)) * r * k)
        for a, b, cc in fs:
            tri = [pts[a], pts[b], pts[cc]]
            self.face(tri, sum(tri, Vector()) / 3 - c, mat=mat)

    def poligono(self, pts2d, z, mat=None, dica=(0, 0, 1)):
        self.face([(x, y, z) for x, y in pts2d], dica, mat=mat)

    def quad_textura(self, p0, ex, ey, dica, mat):
        """Retangulo com UV 0..1 (placas, telas). p0 = canto inferior esquerdo."""
        p0, ex, ey = V(p0), V(ex), V(ey)
        self.face([p0, p0 + ex, p0 + ex + ey, p0 + ey], dica, uv=[(0, 0), (1, 0), (1, 1), (0, 1)], mat=mat)


# ===========================================================================
# CENA / COLECOES
# ===========================================================================
_cols = {}


def colecao(caminho):
    if caminho in _cols:
        return _cols[caminho]
    pai = bpy.context.scene.collection
    acc = ""
    for parte in caminho.split("/"):
        acc = acc + "/" + parte if acc else parte
        if acc not in _cols:
            c = bpy.data.collections.new(parte)
            pai.children.link(c)
            _cols[acc] = c
        pai = _cols[acc]
    return pai


def criar_objeto(nome, malha, caminho):
    if not malha.f:
        return None
    me = bpy.data.meshes.new(nome)
    # origem do objeto no centro da base (facilita mover/girar pecas)
    mn = Vector((min(p.x for p in malha.v), min(p.y for p in malha.v), min(p.z for p in malha.v)))
    mx = Vector((max(p.x for p in malha.v), max(p.y for p in malha.v), max(p.z for p in malha.v)))
    org = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    me.from_pydata([tuple(p - org) for p in malha.v], [], malha.f)
    nomes_mat = []
    for m in malha.mt:
        if m not in nomes_mat:
            nomes_mat.append(m)
    for m in nomes_mat:
        me.materials.append(material(m))
    uvl = me.uv_layers.new(name="UVMap")
    for fi, poly in enumerate(me.polygons):
        tile = MATS[malha.mt[fi]].get("tile", 1.0) if malha.uvw[fi] else 1.0
        for j, li in enumerate(poly.loop_indices):
            u, v = malha.uv[fi][j]
            uvl.data[li].uv = (u / tile, v / tile)
        poly.use_smooth = malha.sm[fi]
        poly.material_index = nomes_mat.index(malha.mt[fi])
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bm.to_mesh(me)
    bm.free()
    me.validate()
    obj = bpy.data.objects.new(nome, me)
    obj.location = org
    colecao(caminho).objects.link(obj)
    return obj


# ===========================================================================
# CONTEINER MARITIMO
# ===========================================================================
PERFIL_P, PERFIL_A, PERFIL_S = 0.278, 0.070, 0.069
PICO, FUNDO = -0.012, 0.036


def corrugado(u0, u1):
    def d(u):
        t = u % PERFIL_P
        a, s = PERFIL_A, PERFIL_S
        if t < a:
            return PICO
        if t < a + s:
            return PICO - FUNDO * (t - a) / s
        if t < 2 * a + s:
            return PICO - FUNDO
        return PICO - FUNDO + FUNDO * (t - 2 * a - s) / (PERFIL_P - 2 * a - s)
    us = {u0, u1}
    k = math.floor(u0 / PERFIL_P)
    while k * PERFIL_P <= u1:
        for off in (0, PERFIL_A, PERFIL_A + PERFIL_S, 2 * PERFIL_A + PERFIL_S):
            u = k * PERFIL_P + off
            if u0 < u < u1:
                us.add(u)
        k += 1
    return [(u, d(u)) for u in sorted(us)]


def solidos(u0, u1, v0, v1, vaos):
    """Divide um painel retangular em retangulos cheios, descontando as aberturas."""
    us = sorted({u0, u1} | {x for a in vaos for x in (a[0], a[1]) if u0 < x < u1})
    res = []
    for a, b in zip(us[:-1], us[1:]):
        if b - a < 1e-6:
            continue
        m = (a + b) / 2
        cortes = sorted((c, d) for (oa, ob, c, d) in vaos if oa <= m <= ob)
        v = v0
        for c, d in cortes:
            if c > v:
                res.append((a, b, v, min(c, v1)))
            v = max(v, d)
        if v < v1:
            res.append((a, b, v, v1))
    return res


class Face:
    """Sistema local de uma face do conteiner: u ao longo da face, v vertical, d para fora."""

    def __init__(self, cont, lado):
        x, y, z, L = cont.x, cont.y, cont.z, cont.L
        self.lado = lado
        if lado == "frente":
            self.o, self.U, self.n, self.Lu = Vector((x, y, z)), Vector((1, 0, 0)), Vector((0, -1, 0)), L
        elif lado == "fundo":
            self.o, self.U, self.n, self.Lu = Vector((x, y + CW, z)), Vector((1, 0, 0)), Vector((0, 1, 0)), L
        elif lado == "esquerda":
            self.o, self.U, self.n, self.Lu = Vector((x, y, z)), Vector((0, 1, 0)), Vector((-1, 0, 0)), CW
        else:
            self.o, self.U, self.n, self.Lu = Vector((x + L, y, z)), Vector((0, 1, 0)), Vector((1, 0, 0)), CW

    def p(self, u, v, d=0.0):
        return self.o + self.U * u + Vector((0, 0, v)) + self.n * d

    def caixa(self, m, u0, u1, v0, v1, d0, d1, mat=None):
        m.caixa(self.p(u0, v0, d0), self.p(u1, v1, d1), mat=mat)


class Conteiner:
    """aberturas: lista de (tipo, lado, u0, u1, v0, v1); tipo = vidro | janela | porta.
    omitir: lados sem parede (ligacao entre dois conteineres = planta livre)."""

    def __init__(self, nome, caminho, x, y, z, L, aberturas=(), omitir=(), interior=True,
                 portas_originais=None, luminarias=True):
        self.nome, self.caminho = nome, caminho
        self.x, self.y, self.z, self.L = x, y, z, L
        self.aberturas = list(aberturas)
        self.omitir = set(omitir)
        self.interior = interior
        self.portas_originais = portas_originais
        self.luminarias = luminarias
        self.construir()

    @property
    def piso(self):
        return self.z + PISO_INT

    def construir(self):
        x, y, z, L = self.x, self.y, self.z, self.L
        c = Malha("Conteiner_Preto")
        e = Malha("Aco_Preto")
        # --- estrutura: colunas de canto, longarinas, cabeceiras e cantoneiras ISO
        for cx in (x, x + L - 0.16):
            for cy in (y, y + CW - 0.16):
                c.caixa((cx, cy, z), (cx + 0.16, cy + 0.16, z + CH), mat="Conteiner_Preto")
        for lado in ("frente", "fundo", "esquerda", "direita"):
            f = Face(self, lado)
            alt_sup = 0.16 if lado in ("frente", "fundo") else 0.22
            f.caixa(c, 0, f.Lu, CH - alt_sup, CH, -0.14, 0)
            f.caixa(c, 0, f.Lu, 0, 0.17, -0.14, 0)
        for cx in (x - 0.004, x + L - 0.174):
            for cy in (y - 0.004, y + CW - 0.158):
                for cz in (z, z + CH - 0.118):
                    c.caixa((cx, cy, cz), (cx + 0.178, cy + 0.162, cz + 0.118), mat="Aco_Preto")
                    # furo oval da cantoneira
                    fy = cy if cy < y + 1 else cy + 0.162
                    sgn = -1 if cy < y + 1 else 1
                    c.caixa((cx + 0.05, fy, cz + 0.035), (cx + 0.128, fy + sgn * 0.003, cz + 0.083),
                            mat="Plastico_Preto")
        # --- cobertura e piso estrutural
        c.caixa((x + 0.1, y + 0.1, z + CH - 0.05), (x + L - 0.1, y + CW - 0.1, z + CH - 0.012))
        c.caixa((x + 0.1, y + 0.1, z + 0.02), (x + L - 0.1, y + CW - 0.1, z + PISO_INT - 0.002), mat="Aco_Preto")
        # --- chapas corrugadas
        for lado in ("frente", "fundo", "esquerda", "direita"):
            if lado in self.omitir:
                continue
            f = Face(self, lado)
            vaos = [(a[2], a[3], a[4], a[5]) for a in self.aberturas if a[1] == lado]
            for (ua, ub, va, vb) in solidos(0.15, f.Lu - 0.15, 0.16, CH - 0.15, vaos):
                pts = corrugado(ua, ub)
                for (u_i, d_i), (u_j, d_j) in zip(pts[:-1], pts[1:]):
                    c.face([f.p(u_i, va, d_i), f.p(u_j, va, d_j), f.p(u_j, vb, d_j), f.p(u_i, vb, d_i)],
                           f.n, mat="Conteiner_Preto")
        # --- revestimento interno (drywall), forro e piso de madeira
        if self.interior:
            ri = Malha("Interior_Branco")
            yi0 = y if "frente" in self.omitir else y + 0.11
            yi1 = y + CW if "fundo" in self.omitir else y + CW - 0.11
            xi0 = x if "esquerda" in self.omitir else x + 0.11
            xi1 = x + L if "direita" in self.omitir else x + L - 0.11
            for lado in ("frente", "fundo", "esquerda", "direita"):
                if lado in self.omitir:
                    continue
                f = Face(self, lado)
                if lado in ("frente", "fundo"):
                    u0, u1 = xi0 - x, xi1 - x
                else:
                    u0, u1 = yi0 - y, yi1 - y
                vaos = [(a[2], a[3], a[4], a[5]) for a in self.aberturas if a[1] == lado]
                for (ua, ub, va, vb) in solidos(u0, u1, PISO_INT, CH - 0.11, vaos):
                    ri.face([f.p(ua, va, -0.11), f.p(ub, va, -0.11), f.p(ub, vb, -0.11), f.p(ua, vb, -0.11)],
                            -f.n)
            ri.poligono([(xi0, yi0), (xi1, yi0), (xi1, yi1), (xi0, yi1)], z + PISO_INT + 0.001,
                        mat="Piso_Madeira")
            ri.poligono([(xi0, yi0), (xi1, yi0), (xi1, yi1), (xi0, yi1)], z + CH - 0.11,
                        mat="Teto_Interior", dica=(0, 0, -1))
            if self.luminarias:
                n = max(1, int((xi1 - xi0) / 2.4))
                for i in range(n):
                    cx = xi0 + (i + 0.5) * (xi1 - xi0) / n
                    cy = (yi0 + yi1) / 2
                    ri.caixa((cx - 0.6, cy - 0.15, z + CH - 0.125), (cx + 0.6, cy + 0.15, z + CH - 0.11),
                             mat="Luz_Teto")
            criar_objeto(f"{self.nome}_Interior", ri, self.caminho)
        # --- portas originais do conteiner (travas verticais)
        if self.portas_originais:
            f = Face(self, self.portas_originais)
            meio = f.Lu / 2
            for (ua, ub) in ((0.17, meio - 0.005), (meio + 0.005, f.Lu - 0.17)):
                f.caixa(c, ua, ub, 0.18, CH - 0.17, -0.03, -0.004, mat="Conteiner_Preto")
                for k in (0.25, 0.75):
                    ub_ = ua + (ub - ua) * k
                    e.cilindro(f.p(ub_, 0.25, 0.02), 0.017, 0.017, CH - 0.5, seg=8, mat="Aco_Galvanizado")
                    f.caixa(e, ub_ - 0.04, ub_ + 0.04, 0.2, 0.28, -0.004, 0.035, mat="Aco_Galvanizado")
                    f.caixa(e, ub_ - 0.04, ub_ + 0.04, CH - 0.28, CH - 0.2, -0.004, 0.035, mat="Aco_Galvanizado")
                    f.caixa(e, ub_ - 0.012, ub_ + 0.012, 1.0, 1.35, 0.02, 0.06, mat="Aco_Galvanizado")
        criar_objeto(f"{self.nome}_Estrutura", c, self.caminho)
        # --- esquadrias, vidros e portas
        for i, (tipo, lado, u0, u1, v0, v1) in enumerate(self.aberturas):
            f = Face(self, lado)
            q = Malha("Aco_Preto")
            w = 0.06
            f.caixa(q, u0 - w, u0, v0 - (w if tipo != "porta" else 0), v1 + w, -0.13, 0.006)
            f.caixa(q, u1, u1 + w, v0 - (w if tipo != "porta" else 0), v1 + w, -0.13, 0.006)
            f.caixa(q, u0 - w, u1 + w, v1, v1 + w, -0.13, 0.006)
            if tipo != "porta":
                f.caixa(q, u0 - w, u1 + w, v0 - w, v0, -0.13, 0.006)
            if tipo in ("vidro", "janela"):
                n = max(1, round((u1 - u0) / 1.2))
                for k in range(1, n):
                    uk = u0 + (u1 - u0) * k / n
                    f.caixa(q, uk - 0.025, uk + 0.025, v0, v1, -0.1, -0.02)
                if tipo == "vidro" and v1 - v0 > 1.8:
                    f.caixa(q, u0, u1, v1 - 0.45, v1 - 0.41, -0.1, -0.02)
                if tipo == "janela":
                    f.caixa(q, u0 - 0.08, u1 + 0.08, v0 - 0.08, v0 - 0.05, -0.02, 0.07, mat="Aco_Galvanizado")
                q.face([f.p(u0, v0, -0.06), f.p(u1, v0, -0.06), f.p(u1, v1, -0.06), f.p(u0, v1, -0.06)],
                       f.n, mat="Vidro")
                nome = "Vidro" if tipo == "vidro" else "Janela"
            else:
                f.caixa(q, u0 + 0.005, u1 - 0.005, v0, v1 - 0.005, -0.08, -0.035, mat="Laranja")
                lado_mac = u1 - 0.1 if (u0 + u1) / 2 < f.Lu / 2 else u0 + 0.1
                f.caixa(q, lado_mac - 0.025, lado_mac + 0.025, 0.98, 1.12, -0.035, -0.005, mat="Aco_Galvanizado")
                sentido = -1 if lado_mac > (u0 + u1) / 2 else 1
                f.caixa(q, lado_mac, lado_mac + sentido * 0.14, 1.03, 1.06, -0.005, 0.03, mat="Aco_Galvanizado")
                if self.luminarias and lado != "fundo":
                    uc = (u0 + u1) / 2
                    f.caixa(q, uc - 0.08, uc + 0.08, v1 + 0.16, v1 + 0.34, 0.0, 0.14, mat="Aco_Preto")
                    f.caixa(q, uc - 0.06, uc + 0.06, v1 + 0.155, v1 + 0.16, 0.02, 0.12, mat="Luz_Externa")
                nome = "Porta"
            criar_objeto(f"{self.nome}_{nome}_{lado}_{i + 1}", q, self.caminho)

    def placa(self, nome, lado, u0, u1, v0, v1, mat):
        f = Face(self, lado)
        m = Malha()
        m.quad_textura(f.p(u0, v0, 0.004), f.U * (u1 - u0), Vector((0, 0, v1 - v0)), f.n, mat)
        criar_objeto(nome, m, self.caminho)


# ===========================================================================
# MOBILIARIO E EQUIPAMENTOS (modelados com a frente para -Y e depois girados)
# ===========================================================================
def colocar(m, x, y, z, rot):
    return m.transformar(rot, (x, y, z))


def mesa(w=1.6, d=0.75, h=0.75, tampo="Madeira_Mesa"):
    m = Malha("Aco_Preto")
    m.caixa((-w / 2, -d / 2, h - 0.03), (w / 2, d / 2, h), mat=tampo)
    for sx in (-1, 1):
        for sy in (-1, 1):
            px, py = sx * (w / 2 - 0.05), sy * (d / 2 - 0.05)
            m.caixa((px - 0.02, py - 0.02, 0), (px + 0.02, py + 0.02, h - 0.03))
    m.caixa((-w / 2 + 0.05, d / 2 - 0.07, h - 0.1), (w / 2 - 0.05, d / 2 - 0.03, h - 0.03))
    return m


def cadeira(cor="Estofado"):
    m = Malha("Aco_Preto")
    m.caixa((-0.23, -0.22, 0.44), (0.23, 0.22, 0.5), mat=cor)
    m.caixa((-0.22, 0.2, 0.55), (0.22, 0.25, 0.95), mat=cor)
    m.caixa((-0.02, 0.2, 0.45), (0.02, 0.24, 0.6))
    m.cilindro((0, 0, 0.06), 0.025, 0.025, 0.38, seg=8)
    for k in range(5):
        a = 2 * math.pi * k / 5
        m.barra((0, 0, 0.07), (0.28 * math.cos(a), 0.28 * math.sin(a), 0.05), 0.04, 0.03)
    return m


def monitor(z_mesa, larg=0.6):
    m = Malha("Plastico_Preto")
    m.caixa((-0.1, -0.08, z_mesa), (0.1, 0.08, z_mesa + 0.015))
    m.caixa((-0.025, 0.01, z_mesa), (0.025, 0.04, z_mesa + 0.18))
    h = larg * 0.58
    m.caixa((-larg / 2, -0.02, z_mesa + 0.12), (larg / 2, 0.01, z_mesa + 0.12 + h))
    m.quad_textura((-larg / 2 + 0.015, -0.0205, z_mesa + 0.135), (larg - 0.03, 0, 0), (0, 0, h - 0.03),
                   (0, -1, 0), "Tela_CAD")
    m.caixa((-0.22, -0.3, z_mesa), (0.22, -0.16, z_mesa + 0.02))  # teclado
    return m


def tv(larg=1.4, ligada=False):
    m = Malha("Plastico_Preto")
    h = larg * 0.5625
    m.caixa((-larg / 2, -0.05, -h / 2), (larg / 2, 0, h / 2))
    m.quad_textura((-larg / 2 + 0.02, -0.0505, -h / 2 + 0.02), (larg - 0.04, 0, 0), (0, 0, h - 0.04), (0, -1, 0),
                   "Tela_CAD" if ligada else "Tela_Desligada")
    return m


def estante(w=1.0, d=0.4, h=1.9, rng=None):
    m = Malha("Aco_Preto")
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.caixa((sx * w / 2 - 0.02 * (sx > 0), sy * d / 2 - 0.02 * (sy > 0), 0),
                    (sx * w / 2 + 0.02 * (sx < 0), sy * d / 2 + 0.02 * (sy < 0), h))
    for k in range(5):
        zz = 0.08 + k * (h - 0.1) / 4
        m.caixa((-w / 2, -d / 2, zz), (w / 2, d / 2, zz + 0.02), mat="Aco_Galvanizado")
        if rng and k < 4:
            xx = -w / 2 + 0.05
            while xx < w / 2 - 0.15:
                bw = rng.uniform(0.12, 0.3)
                bh = rng.uniform(0.12, 0.3)
                cor = rng.choice(["Livros_Caixas", "Laranja", "Azul_Detalhe", "Plastico_Preto", "Quadro_Eletrico"])
                m.caixa((xx, -d / 2 + 0.05, zz + 0.02), (min(xx + bw, w / 2 - 0.04), d / 2 - 0.05, zz + 0.02 + bh),
                        mat=cor)
                xx += bw + rng.uniform(0.02, 0.1)
    return m


def impressora3d(z):
    m = Malha("Plastico_Preto")
    m.caixa((-0.22, -0.22, z), (0.22, 0.22, z + 0.06))
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.caixa((sx * 0.2 - 0.015, sy * 0.2 - 0.015, z), (sx * 0.2 + 0.015, sy * 0.2 + 0.015, z + 0.5))
    m.caixa((-0.22, -0.22, z + 0.48), (0.22, 0.22, z + 0.52))
    m.caixa((-0.15, -0.15, z + 0.12), (0.15, 0.15, z + 0.13), mat="Aco_Galvanizado")
    m.caixa((-0.04, -0.04, z + 0.25), (0.04, 0.04, z + 0.32), mat="Laranja")
    m.caixa((-0.2, -0.01, z + 0.3), (0.2, 0.01, z + 0.32), mat="Aco_Galvanizado")
    return m


def torno(comp=2.0):
    """Torno mecanico simplificado."""
    m = Malha("Cinza_Maquina")
    m.caixa((-comp / 2, -0.3, 0), (comp / 2, 0.3, 0.75))
    m.caixa((-comp / 2, -0.25, 0.75), (comp / 2, 0.25, 0.85), mat="Aco_Galvanizado")
    m.caixa((-comp / 2, -0.3, 0.85), (-comp / 2 + 0.55, 0.3, 1.35))
    m.caixa((comp / 2 - 0.35, -0.2, 0.85), (comp / 2 - 0.05, 0.2, 1.15))
    m.cilindro((-comp / 2 + 0.55, 0, 1.1), 0.13, 0.13, 0.08, seg=16, eixo=(1, 0, 0), mat="Aco_Galvanizado")
    m.caixa((-0.2, -0.3, 0.85), (0.2, 0.2, 1.0), mat="Laranja")
    m.caixa((-comp / 2 + 0.1, -0.31, 0.95), (-comp / 2 + 0.45, -0.3, 1.25), mat="Quadro_Eletrico")
    return m


def fresadora():
    m = Malha("Cinza_Maquina")
    m.caixa((-0.45, -0.4, 0), (0.45, 0.4, 0.9))
    m.caixa((-0.6, -0.3, 0.9), (0.6, 0.3, 0.98), mat="Aco_Galvanizado")
    m.caixa((-0.25, 0.1, 0.9), (0.25, 0.4, 2.0))
    m.caixa((-0.2, -0.25, 1.5), (0.2, 0.15, 1.9), mat="Laranja")
    m.cilindro((0, -0.05, 1.25), 0.05, 0.03, 0.25, seg=12, mat="Aco_Galvanizado")
    return m


def braco_robotico(z):
    m = Malha("Laranja")
    m.cilindro((0, 0, z), 0.16, 0.16, 0.08, seg=20, mat="Plastico_Preto")
    m.cilindro((0, 0, z + 0.08), 0.11, 0.1, 0.22, seg=20)
    ombro = Vector((0, 0, z + 0.36))
    cot = ombro + Vector((0.12, -0.18, 0.42))
    pun = cot + Vector((0.08, -0.36, -0.12))
    m.cilindro(ombro + Vector((-0.09, 0, 0)), 0.08, 0.08, 0.18, seg=16, eixo=(1, 0, 0), mat="Plastico_Preto")
    m.barra(ombro, cot, 0.11)
    m.cilindro(cot + Vector((-0.07, 0, 0)), 0.065, 0.065, 0.14, seg=16, eixo=(1, 0, 0), mat="Plastico_Preto")
    m.barra(cot, pun, 0.08)
    m.barra(pun, pun + Vector((0, -0.04, -0.12)), 0.05, mat="Plastico_Preto")
    m.caixa(pun + Vector((-0.05, -0.06, -0.2)), pun + Vector((-0.03, -0.02, -0.12)), mat="Aco_Galvanizado")
    m.caixa(pun + Vector((0.03, -0.06, -0.2)), pun + Vector((0.05, -0.02, -0.12)), mat="Aco_Galvanizado")
    return m


def painel_eletrico(w=0.8, h=1.8, d=0.3):
    m = Malha("Quadro_Eletrico")
    m.caixa((-w / 2, -d / 2, 0.1), (w / 2, d / 2, 0.1 + h))
    m.caixa((-0.005, -d / 2 - 0.005, 0.15), (0.005, -d / 2, 0.05 + h), mat="Plastico_Preto")
    m.caixa((-w / 2 + 0.08, -d / 2 - 0.01, 1.3), (-w / 2 + 0.3, -d / 2, 1.5), mat="Tela_Desligada")
    for k, cor in enumerate(["Laranja", "Azul_Detalhe", "Luz_Externa"]):
        m.cilindro((w / 2 - 0.12 - 0.08 * k, -d / 2, 1.4), 0.025, 0.025, 0.02, seg=10, eixo=(0, -1, 0), mat=cor)
    m.caixa((-w / 2 + 0.06, -d / 2 - 0.02, 1.85), (w / 2 - 0.06, -d / 2 + 0.01, 1.9), mat="Aco_Preto")
    return m


def bancada_didatica():
    """Bancada de automacao com painel de CLP."""
    m = mesa(1.8, 0.8, 0.85, tampo="Cinza_Maquina")
    m.caixa((-0.85, 0.25, 0.85), (0.85, 0.3, 1.75), mat="Aco_Galvanizado")
    for i in range(6):
        for j in range(3):
            cor = ["Quadro_Eletrico", "Azul_Detalhe", "Plastico_Preto"][j]
            x0 = -0.75 + i * 0.25
            m.caixa((x0, 0.22, 0.95 + j * 0.25), (x0 + 0.18, 0.25, 1.13 + j * 0.25), mat=cor)
    m.caixa((-0.85, 0.24, 1.66), (0.85, 0.25, 1.7), mat="Laranja")
    return m


def quadro_branco(w=1.6, h=1.0, z0=0.9, pes=False):
    m = Malha("Aco_Galvanizado")
    if pes:
        for sx in (-1, 1):
            m.caixa((sx * w / 2 - 0.02, -0.02, 0.05), (sx * w / 2 + 0.02, 0.02, z0 + h))
            m.caixa((sx * w / 2 - 0.03, -0.3, 0.0), (sx * w / 2 + 0.03, 0.3, 0.05), mat="Aco_Preto")
    m.caixa((-w / 2, -0.03, z0), (w / 2, 0, z0 + h))
    m.caixa((-w / 2 + 0.02, -0.031, z0 + 0.02), (w / 2 - 0.02, -0.03, z0 + h - 0.02), mat="Quadro_Branco")
    m.caixa((-w / 2, -0.09, z0 - 0.02), (w / 2, 0, z0), mat="Aco_Galvanizado")
    return m


def sofa(w=1.8):
    m = Malha("Estofado")
    m.caixa((-w / 2, -0.4, 0.1), (w / 2, 0.4, 0.42))
    m.caixa((-w / 2, 0.22, 0.42), (w / 2, 0.4, 0.8))
    m.caixa((-w / 2, -0.4, 0.42), (-w / 2 + 0.15, 0.4, 0.62))
    m.caixa((w / 2 - 0.15, -0.4, 0.42), (w / 2, 0.4, 0.62))
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.caixa((sx * (w / 2 - 0.06) - 0.02, sy * 0.34 - 0.02, 0), (sx * (w / 2 - 0.06) + 0.02, sy * 0.34 + 0.02, 0.1),
                    mat="Aco_Preto")
    return m


def posto_trabalho(nome, caminho, x, y, z, rot, rng, com_monitor=True, larg=1.6, dupla=False):
    m = mesa(larg, 0.75)
    if com_monitor:
        mon = monitor(0.75)
        mon.transformar(0, (-0.3 if dupla else 0, 0.12, 0))
        m.juntar(mon)
        if dupla:
            m2 = monitor(0.75)
            m2.transformar(0, (0.35, 0.12, 0))
            m.juntar(m2)
    criar_objeto(f"{nome}_Mesa", colocar(m, x, y, z, rot), caminho)
    c = cadeira()
    c.transformar(180 + rng.uniform(-15, 15), (0, -0.55, 0))
    criar_objeto(f"{nome}_Cadeira", colocar(c, x, y, z, rot), caminho)


# ===========================================================================
# PAISAGISMO
# ===========================================================================
def arbusto(m, x, y, z, r, rng, mat="Folhagem"):
    for _ in range(rng.randint(3, 5)):
        dx, dy = rng.uniform(-0.35, 0.35) * r, rng.uniform(-0.35, 0.35) * r
        rr = r * rng.uniform(0.6, 0.85)
        m.esfera((x + dx, y + dy, z + rr * 0.75), rr, rng, 0.12, (1, 1, 0.85),
                 mat=rng.choice([mat, mat, "Folhagem_Clara", "Folhagem_Escura"]))


def vaso_planta(nome, caminho, x, y, rng):
    m = Malha("Vaso")
    m.cilindro((x, y, BASE), 0.22, 0.28, 0.62, seg=20)
    m.cilindro((x, y, BASE + 0.58), 0.25, 0.25, 0.01, seg=20, mat="Terra")
    arbusto(m, x, y, BASE + 0.55, 0.42, rng)
    criar_objeto(nome, m, caminho)


def arvore(m, x, y, h, r, rng, tipo="folhosa"):
    if tipo == "pinheiro":
        m.cilindro((x, y, 0), 0.22, 0.1, h * 0.92, seg=9, mat="Tronco")
        for k in range(rng.randint(7, 11)):
            zz = h * rng.uniform(0.6, 0.97)
            ang = rng.uniform(0, 2 * math.pi)
            dd = r * rng.uniform(0.15, 0.7) * (1.15 - zz / h)
            m.esfera((x + math.cos(ang) * dd, y + math.sin(ang) * dd, zz), r * rng.uniform(0.4, 0.55), rng, 0.3,
                     (1.2, 1.2, 0.75), mat="Pinheiro")
    else:
        m.cilindro((x, y, 0), 0.18, 0.1, h * 0.55, seg=8, mat="Tronco")
        for k in range(rng.randint(4, 7)):
            ang = rng.uniform(0, 2 * math.pi)
            dd = r * rng.uniform(0.1, 0.6)
            zz = h * rng.uniform(0.55, 0.85)
            m.esfera((x + math.cos(ang) * dd, y + math.sin(ang) * dd, zz), r * rng.uniform(0.5, 0.8), rng, 0.2,
                     (1, 1, 0.85), mat=rng.choice(["Folhagem", "Folhagem_Escura", "Folhagem_Clara"]))


def balizador(m, x, y):
    m.cilindro((x, y, 0), 0.07, 0.07, 0.55, seg=12, mat="Aco_Preto")
    m.cilindro((x, y, 0.55), 0.075, 0.075, 0.06, seg=12, mat="Luz_Externa")
    m.cilindro((x, y, 0.61), 0.085, 0.085, 0.03, seg=12, mat="Aco_Preto")


# ===========================================================================
# MONTAGEM DA CENA
# ===========================================================================
def limpar_cena():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    for blocos in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.cameras, bpy.data.lights,
                   bpy.data.worlds):
        for b in list(blocos):
            blocos.remove(b)
    _cols.clear()
    _cache_mat.clear()


def bloco_mecanica(rng):
    cam = "01_Bloco_Engenharia_Mecanica"
    ce = cam + "/Conteineres"
    x = X_MEC
    t1 = Conteiner("MEC_Terreo_Frente", ce, x, 0, BASE, L40, omitir=["fundo"], portas_originais="esquerda",
                   aberturas=[("vidro", "frente", 2.4, 7.6, 0.25, 2.62),
                              ("porta", "frente", 10.75, 11.7, 0.17, 2.3),
                              ("porta", "direita", 0.75, 1.65, 0.17, 2.3)])
    Conteiner("MEC_Terreo_Fundo", ce, x, CW, BASE, L40, omitir=["frente"],
              aberturas=[("janela", "fundo", 2.0, 3.8, 1.0, 2.2), ("janela", "fundo", 8.0, 9.8, 1.0, 2.2)])
    s1 = Conteiner("MEC_Superior", ce, x + 1.5, 0, BASE + CH, L30,
                   aberturas=[("janela", "fundo", 3.0, 4.8, 1.0, 2.2), ("janela", "fundo", 6.0, 7.8, 1.0, 2.2)])
    s1.placa("MEC_Placa_Fachada", "frente", 1.1, 7.6, 0.75, 2.07, "Placa_Mecanica")
    # interior: laboratorio de mecanica
    ci = cam + "/Interior"
    zf = t1.piso
    for i, xx in enumerate((3.3, 5.0, 6.7)):
        posto_trabalho(f"MEC_Posto_{i + 1}", ci, x + xx, 1.45, zf, 0, rng, larg=1.5)
    m = tv(1.6)
    criar_objeto("MEC_TV_Parede", colocar(m, x + 3.6, 2 * CW - 0.115, zf + 1.6, 0), ci)
    m = mesa(3.0, 0.8, 0.9, tampo="Madeira_Mesa")
    m.juntar(impressora3d(0.9).transformar(0, (-0.9, 0, 0)))
    m.juntar(impressora3d(0.9).transformar(0, (-0.3, 0, 0)))
    criar_objeto("MEC_Bancada_Impressao3D", colocar(m, x + 7.6, 4.35, zf, 180), ci)
    criar_objeto("MEC_Torno", colocar(torno(2.0), x + 10.4, 3.9, zf, 0), ci)
    criar_objeto("MEC_Fresadora", colocar(fresadora(), x + 8.9, 1.25, zf, 0), ci)
    criar_objeto("MEC_Estante_1", colocar(estante(rng=rng), x + 0.35, 3.0, zf, 90), ci)
    criar_objeto("MEC_Estante_2", colocar(estante(rng=rng), x + 0.35, 4.1, zf, 90), ci)
    # condensadora de ar-condicionado nos fundos
    m = Malha("Condensadora")
    m.caixa((x + 5.0, 2 * CW + 0.02, BASE + 0.45), (x + 5.85, 2 * CW + 0.34, BASE + 1.05))
    m.cilindro((x + 5.3, 2 * CW + 0.34, BASE + 0.75), 0.2, 0.2, 0.005, seg=20, eixo=(0, 1, 0), mat="Plastico_Preto")
    m.caixa((x + 4.95, 2 * CW, BASE + 0.4), (x + 5.9, 2 * CW + 0.38, BASE + 0.45), mat="Aco_Galvanizado")
    criar_objeto("MEC_Condensadora_AC", m, cam)


def pergolado(rng):
    cam = "02_Pergolado_Area_Convivencia"
    y0, y1 = -1.2, 6.9
    zt = BASE + 4.2
    m = Malha("Aco_Preto")
    pil_x = (X_PERG0 + 0.075, (X_PERG0 + X_PERG1) / 2, X_PERG1 - 0.075)
    for px in pil_x:
        for py in (y0, y1):
            m.caixa((px - 0.075, py - 0.075, BASE), (px + 0.075, py + 0.075, zt))
            m.caixa((px - 0.15, py - 0.15, BASE), (px + 0.15, py + 0.15, BASE + 0.012), mat="Aco_Galvanizado")
        m.caixa((px - 0.06, y0, zt - 0.3), (px + 0.06, y1, zt))  # vigas transversais
    for py in (y0, y1):
        m.caixa((X_PERG0, py - 0.075, zt - 0.3), (X_PERG1, py + 0.075, zt))  # vigas longitudinais
    xr0, xr1 = X_PERG0 - 0.2, X_AUT + 2.9
    yy = y0 - 0.25
    while yy <= y1 + 0.26:
        m.caixa((xr0, yy - 0.03, zt), (xr1, yy + 0.03, zt + 0.12))  # tercas
        yy += 0.95
    criar_objeto("PERG_Estrutura_Metalica", m, cam)
    # telha trapezoidal
    t = Malha("Telha_Metalica")
    ya, yb = y0 - 0.35, y1 + 0.35
    for (ua, da), (ub, db) in zip(corrugado(ya, yb)[:-1], corrugado(ya, yb)[1:]):
        za, zb = zt + 0.12 + 0.05 + da, zt + 0.12 + 0.05 + db
        t.face([(xr0, ua, za), (xr1, ua, za), (xr1, ub, zb), (xr0, ub, zb)], (0, 0, 1))
        t.face([(xr0, ua, za - 0.003), (xr0, ub, zb - 0.003), (xr1, ub, zb - 0.003), (xr1, ua, za - 0.003)],
               (0, 0, -1))
    for yb_ in (ya, yb):
        t.caixa((xr0 - 0.02, yb_ - 0.02, zt + 0.06), (xr1 + 0.02, yb_ + 0.02, zt + 0.2), mat="Aco_Preto")
    criar_objeto("PERG_Cobertura_Telha", t, cam)
    # piso de concreto
    p = Malha("Concreto")
    p.caixa((X_PERG0 - 0.3, -1.6, -0.1), (X_AUT, y1 + 0.4, BASE))
    criar_objeto("PERG_Piso_Concreto", p, cam)
    # pendentes
    lum = Malha("Aco_Preto")
    for lx in (X_PERG0 + 2.0, X_PERG0 + 5.8):
        for ly in (0.6, 2.9, 5.2):
            lum.caixa((lx - 0.005, ly - 0.005, zt - 1.0), (lx + 0.005, ly + 0.005, zt))
            lum.cilindro((lx, ly, zt - 1.2), 0.25, 0.06, 0.22, seg=20)
            lum.cilindro((lx, ly, zt - 1.21), 0.12, 0.12, 0.02, seg=16, mat="Luz_Externa")
    criar_objeto("PERG_Luminarias_Pendentes", lum, cam)
    # mobiliario: bancadas de trabalho, cadeiras e monitores
    cm = cam + "/Mobiliario"
    k = 0
    for ly in (0.7, 3.3):
        for lx in (X_PERG0 + 1.45, X_PERG0 + 3.85, X_PERG0 + 6.25):
            k += 1
            mm = mesa(2.0, 0.85, 0.76)
            for dx in (-0.5, 0.5):
                if rng.random() < 0.75:
                    mm.juntar(monitor(0.76, 0.55).transformar(0, (dx, 0.18, 0)))
            criar_objeto(f"PERG_Bancada_{k}", colocar(mm, lx, ly, BASE, 0), cm)
            for dx in (-0.5, 0.5):
                c = cadeira()
                c.transformar(180 + rng.uniform(-20, 20), (dx, -0.65, 0))
                criar_objeto(f"PERG_Cadeira_{k}", colocar(c, lx, ly, BASE, 0), cm)
    criar_objeto("PERG_Quadro_Branco_Movel", colocar(quadro_branco(1.8, 1.0, pes=True), X_PERG0 + 2.6, 6.4, BASE, 0),
                 cm)
    criar_objeto("PERG_Sofa", colocar(sofa(2.0), X_PERG0 + 6.4, 5.9, BASE, 0), cm)
    mc = Malha("Madeira_Mesa")
    mc.caixa((-0.5, -0.3, 0.35), (0.5, 0.3, 0.4))
    mc.caixa((-0.45, -0.25, 0), (0.45, 0.25, 0.35), mat="Aco_Preto")
    criar_objeto("PERG_Mesa_Centro", colocar(mc, X_PERG0 + 6.4, 5.0, BASE, 0), cm)


def bloco_automacao(rng):
    cam = "03_Bloco_Engenharia_Automacao"
    ce = cam + "/Conteineres"
    x = X_AUT
    t1 = Conteiner("AUT_Terreo_Frente", ce, x, 0, BASE, L40, omitir=["fundo"],
                   aberturas=[("vidro", "frente", 0.6, 2.4, 0.25, 2.62),
                              ("vidro", "frente", 4.2, 8.7, 0.25, 2.62),
                              ("porta", "frente", 10.6, 11.55, 0.17, 2.3),
                              ("porta", "esquerda", 0.75, 1.65, 0.17, 2.3)])
    Conteiner("AUT_Terreo_Fundo", ce, x, CW, BASE, L40, omitir=["frente"],
              aberturas=[("janela", "fundo", 3.0, 4.8, 1.0, 2.2), ("janela", "fundo", 7.5, 9.3, 1.0, 2.2)])
    s1 = Conteiner("AUT_Superior", ce, x + L40 - L30, 0, BASE + CH, L30,
                   aberturas=[("janela", "esquerda", 0.5, 1.9, 1.0, 2.2), ("janela", "fundo", 4.0, 5.8, 1.0, 2.2)])
    s1.placa("AUT_Placa_Fachada", "frente", 2.2, 8.3, 0.85, 2.11, "Placa_Automacao")
    ci = cam + "/Interior"
    zf = t1.piso
    for i, xx in enumerate((5.2, 7.4)):
        posto_trabalho(f"AUT_Posto_{i + 1}", ci, x + xx, 1.4, zf, 0, rng, larg=1.8, dupla=True)
    m = mesa(1.4, 0.8, 0.8, tampo="Cinza_Maquina")
    m.juntar(braco_robotico(0.8))
    criar_objeto("AUT_Celula_Robotica", colocar(m, x + 1.6, 1.4, zf, 0), ci)
    criar_objeto("AUT_Bancada_CLP_1", colocar(bancada_didatica(), x + 3.6, 4.3, zf, 0), ci)
    criar_objeto("AUT_Bancada_CLP_2", colocar(bancada_didatica(), x + 6.0, 4.3, zf, 0), ci)
    criar_objeto("AUT_Painel_Eletrico", colocar(painel_eletrico(), x + 9.2, 4.55, zf, 0), ci)
    criar_objeto("AUT_Estante", colocar(estante(rng=rng), x + 11.7, 3.6, zf, 270), ci)
    criar_objeto("AUT_TV_Parede", colocar(tv(1.4, True), x + 0.115, 3.3, zf + 1.6, 90), ci)
    m = Malha("Condensadora")
    m.caixa((x + 6.0, 2 * CW + 0.02, BASE + 0.45), (x + 6.85, 2 * CW + 0.34, BASE + 1.05))
    m.cilindro((x + 6.3, 2 * CW + 0.34, BASE + 0.75), 0.2, 0.2, 0.005, seg=20, eixo=(0, 1, 0), mat="Plastico_Preto")
    criar_objeto("AUT_Condensadora_AC", m, cam)


def escada():
    cam = "04_Escada_Metalica"
    z_topo = BASE + CH + PISO_INT
    n_esp = 17
    esp = (z_topo - BASE) / n_esp
    pisada = 0.255
    x0 = ESCADA_X0
    x_pat = x0 + (n_esp - 1) * pisada
    ya, yb = -1.35, -0.15
    m = Malha("Aco_Preto")
    inc = esp / pisada
    # longarinas
    for yy in (ya, yb - 0.06):
        xs, xe = x0 - 0.25, x_pat
        za = BASE + esp + (xs - x0) * inc + 0.05
        ze = BASE + esp + (xe - x0) * inc + 0.05
        perp = Vector((inc, 0, -1)).normalized() * 0.28
        m.paralelepipedo((xs, yy, za), (xe - xs, 0, ze - za), (0, 0.06, 0), perp)
    # degraus (chapa xadrez)
    for k in range(1, n_esp):
        zk = BASE + k * esp
        xa = x0 + (k - 1) * pisada
        m.caixa((xa - 0.01, ya + 0.06, zk - 0.035), (xa + pisada + 0.01, yb - 0.06, zk), mat="Aco_Galvanizado")
        m.caixa((xa - 0.01, ya + 0.06, zk - 0.08), (xa + 0.02, yb - 0.06, zk - 0.035))
    # patamar
    m.caixa((x_pat, ya, z_topo - 0.06), (x_pat + 1.35, -0.005, z_topo), mat="Aco_Galvanizado")
    m.caixa((x_pat, ya, z_topo - 0.22), (x_pat + 1.35, ya + 0.08, z_topo - 0.06))
    for px in (x_pat + 0.05, x_pat + 1.3):
        m.caixa((px - 0.05, ya, BASE), (px + 0.05, ya + 0.1, z_topo - 0.06))
    # guarda-corpos
    for yy in (ya + 0.03, yb - 0.03):
        h_c = 0.95
        p_a = Vector((x0 - 0.1, yy, BASE + esp + h_c))
        p_b = Vector((x_pat, yy, z_topo + h_c - 0.03))
        m.barra(p_a, p_b, 0.045)
        m.barra(p_a + Vector((0.1, 0, -0.45)), p_b + Vector((0, 0, -0.45)), 0.03)
        for k in range(0, n_esp, 4):
            xb = x0 + k * pisada + 0.1
            zb = BASE + (k + 1) * esp
            m.caixa((xb - 0.02, yy - 0.02, zb), (xb + 0.02, yy + 0.02, zb + h_c))
    # guarda-corpo do patamar
    xe = x_pat + 1.35
    for (pa, pb) in (((x_pat, ya + 0.03), (xe - 0.03, ya + 0.03)), ((xe - 0.03, ya + 0.03), (xe - 0.03, -0.03))):
        for hh in (0.45, 1.0):
            m.barra((pa[0], pa[1], z_topo + hh), (pb[0], pb[1], z_topo + hh), 0.045 if hh > 0.9 else 0.03)
        for t in (0.0, 0.5, 1.0):
            px = pa[0] + (pb[0] - pa[0]) * t
            py = pa[1] + (pb[1] - pa[1]) * t
            m.caixa((px - 0.02, py - 0.02, z_topo), (px + 0.02, py + 0.02, z_topo + 1.0))
        m.caixa((min(pa[0], pb[0]) - 0.02, min(pa[1], pb[1]) - 0.005, z_topo),
                (max(pa[0], pb[0]) + 0.02, max(pa[1], pb[1]) + 0.005, z_topo + 0.1))
    criar_objeto("ESC_Escada_e_Patamar", m, cam)


def bloco_salas(rng):
    cam = "05_Bloco_Salas_Projetos_Reunioes"
    ce = cam + "/Conteineres"
    x = X_SALAS
    t1 = Conteiner("SAL_Terreo_Frente", ce, x, 0, BASE, L40, omitir=["fundo"],
                   aberturas=[("porta", "frente", 4.95, 5.85, 0.17, 2.3),
                              ("janela", "frente", 6.7, 9.5, 0.9, 2.3),
                              ("vidro", "frente", 10.45, 11.95, 0.25, 2.62),
                              ("vidro", "direita", 0.25, 2.2, 0.25, 2.62)])
    Conteiner("SAL_Terreo_Fundo", ce, x, CW, BASE, L40, omitir=["frente"],
              aberturas=[("janela", "fundo", 2.0, 3.8, 1.0, 2.2), ("janela", "fundo", 8.0, 9.8, 1.0, 2.2),
                         ("janela", "direita", 0.5, 2.0, 1.0, 2.2)])
    s1 = Conteiner("SAL_Superior_Frente", ce, x, 0, BASE + CH, L40, omitir=["fundo"],
                   aberturas=[("porta", "frente", 2.05, 2.95, 0.17, 2.3),
                              ("vidro", "frente", 10.45, 11.95, 0.25, 2.62),
                              ("vidro", "direita", 0.25, 2.2, 0.25, 2.62)])
    Conteiner("SAL_Superior_Fundo", ce, x, CW, BASE + CH, L40, omitir=["frente"],
              aberturas=[("janela", "fundo", 3.0, 4.8, 1.0, 2.2), ("janela", "fundo", 8.5, 10.3, 1.0, 2.2),
                         ("janela", "direita", 0.5, 2.0, 1.0, 2.2)])
    s1.placa("SAL_Placa_Projetos", "frente", 3.35, 6.35, 1.18, 2.18, "Placa_Projetos")
    s1.placa("SAL_Placa_Reunioes", "frente", 6.7, 10.1, 1.18, 2.18, "Placa_Reunioes")
    # --- terreo: prototipagem
    ci = cam + "/Interior_Terreo_Prototipagem"
    zf = t1.piso
    for i, xx in enumerate((2.0, 4.6)):
        m = mesa(2.2, 0.9, 0.9)
        m.juntar(impressora3d(0.9).transformar(0, (-0.6, 0.1, 0)))
        m.juntar(impressora3d(0.9).transformar(0, (0.2, 0.1, 0)))
        criar_objeto(f"SAL_Bancada_Prototipos_{i + 1}", colocar(m, x + xx, 3.2, zf, 0), ci)
    for i, xx in enumerate((1.0, 2.2, 3.4, 4.6, 5.8)):
        criar_objeto(f"SAL_Estante_{i + 1}", colocar(estante(1.1, rng=rng), x + xx, 4.55, zf, 0), ci)
    posto_trabalho("SAL_Posto_Terreo_1", ci, x + 8.2, 1.4, zf, 0, rng, larg=1.6, dupla=True)
    criar_objeto("SAL_Sofa_Terreo", colocar(sofa(1.9), x + 11.2, 3.6, zf, 270), ci)
    criar_objeto("SAL_Fresadora_CNC", colocar(fresadora(), x + 9.3, 4.2, zf, 0), ci)
    # --- superior: sala de projetos e sala de reunioes
    zs = s1.piso
    xdiv = x + 6.45
    m = Malha("Interior_Branco")
    m.caixa((xdiv - 0.05, 0.11, zs), (xdiv + 0.05, 2 * CW - 0.11, BASE + 2 * CH - 0.11))
    criar_objeto("SAL_Divisoria_Drywall", m, cam + "/Interior_Superior")
    cp = cam + "/Interior_Superior/Sala_de_Projetos"
    for i, (xx, yy) in enumerate(((1.8, 3.6), (3.9, 3.6), (1.8, 1.6), (4.2, 1.6))):
        posto_trabalho(f"SAL_Projetos_Posto_{i + 1}", cp, x + xx, yy, zs, 0 if yy > 3 else 180, rng, larg=1.6,
                       dupla=i % 2 == 0)
    criar_objeto("SAL_Projetos_Quadro_Branco", colocar(quadro_branco(2.0, 1.1), xdiv - 0.05, 2.5, zs, 270), cp)
    cr = cam + "/Interior_Superior/Sala_de_Reunioes"
    xm, ym = x + 9.1, 2.45
    m = mesa(3.0, 1.15, 0.75)
    criar_objeto("SAL_Reunioes_Mesa", colocar(m, xm, ym, zs, 90), cr)
    for k, (dx, dy, rot) in enumerate([(-1.0, -0.85, 90), (0.0, -0.85, 90), (1.0, -0.85, 90),
                                       (-1.0, 0.85, 270), (0.0, 0.85, 270), (1.0, 0.85, 270),
                                       (1.85, 0, 0)]):
        c = cadeira()
        c.transformar(rot + rng.uniform(-10, 10), (0, 0, 0))
        criar_objeto(f"SAL_Reunioes_Cadeira_{k + 1}", colocar(c, xm + dy, ym + dx, zs, 0), cr)
    criar_objeto("SAL_Reunioes_TV", colocar(tv(1.8, True), xdiv + 0.05, ym, zs + 1.5, 90), cr)
    vaso_planta("SAL_Reunioes_Vaso", cr, x + 11.6, 4.4, rng)


def terreno_e_paisagismo(rng):
    cam = "06_Terreno_e_Paisagismo"
    # meio-fio diagonal (lado esquerdo proximo, lado direito afastado)
    def y_meio_fio(xx):
        return MEIO_FIO_Y0 - (xx + 3.0) * MEIO_FIO_INCL
    xa, xb = -8.0, 52.0
    m = Malha("Grama_Campo")
    m.poligono([(-250, -250), (300, -250), (300, 300), (-250, 300)], -0.01)
    criar_objeto("TER_Campo_Gramado", m, cam)
    m = Malha("Grama")
    m.poligono([(xa, -1.6), (xb, -1.6), (xb, y_meio_fio(xb)), (xa, y_meio_fio(xa))], 0.012)
    criar_objeto("TER_Gramado_Frontal", m, cam)
    m = Malha("Brita")
    m.poligono([(xa, y_meio_fio(xa)), (xb, y_meio_fio(xb)), (xb, -70), (xa, -70)], 0.004)
    criar_objeto("TER_Estacionamento_Brita", m, cam)
    m = Malha("Concreto")
    m.caixa((-1.6, -1.6, -0.1), (X_PERG0 - 0.3, 0, BASE))
    m.caixa((X_AUT, -1.6, -0.1), (X_SALAS + L40 + 1.6, 0, BASE))
    m.caixa((X_SALAS + L40, 0, -0.1), (X_SALAS + L40 + 1.6, 2 * CW + 1.0, BASE))
    criar_objeto("TER_Calcada_Concreto", m, cam)
    m = Malha("Concreto_Meio_Fio")
    m.barra((xa, y_meio_fio(xa), 0.04), (xb, y_meio_fio(xb), 0.04), 0.15, 0.2)
    m.barra((20.0, -50.0, 0.04), (44.0, y_meio_fio(44.0), 0.04), 0.15, 0.2)
    criar_objeto("TER_Meio_Fio", m, cam)
    m = Malha("Paralelepipedo")
    m.poligono([(20.0, -52.6), (20.0, -50.0), (44.0, y_meio_fio(44.0)), (47.4, y_meio_fio(47.4))], 0.03)
    criar_objeto("TER_Calcada_Paralelepipedo", m, cam)
    # arbustos ao longo do meio-fio e junto a placa
    m = Malha("Folhagem")
    xx = -6.5
    while xx < 21.0:
        arbusto(m, xx, y_meio_fio(xx) + 0.7, 0.0, rng.uniform(0.38, 0.5), rng)
        xx += rng.uniform(1.25, 1.5)
    arbusto(m, PLACA_XY[0] + 3.1, PLACA_XY[1] - 0.6, 0.0, 0.62, rng)
    arbusto(m, PLACA_XY[0] + 4.4, PLACA_XY[1] - 0.2, 0.0, 0.58, rng)
    criar_objeto("TER_Arbustos", m, cam)
    for i, (vx, vy) in enumerate(((-0.75, -0.75), (12.2, -0.75), (23.45, -0.7), (32.3, -0.6))):
        vaso_planta(f"TER_Vaso_Planta_{i + 1}", cam, vx, vy, rng)
    m = Malha("Aco_Preto")
    for bx, by in ((3.5, -2.2), (10.5, -2.2), (17.0, -2.2), (26.0, -2.2), (34.0, -2.2), (43.5, -2.2),
                   (12.0, y_meio_fio(12.0) + 1.6), (36.0, y_meio_fio(36.0) + 1.6)):
        balizador(m, bx, by)
    criar_objeto("TER_Balizadores_Luminosos", m, cam)


def placa_principal():
    cam = "07_Placa_Laboratorio"
    cx, cy = PLACA_XY
    w, h, z0 = 3.3, 1.35, 0.5
    m = Malha("Placa_Fundo")
    m.caixa((cx - w / 2, cy, z0), (cx + w / 2, cy + 0.08, z0 + h))
    m.quad_textura((cx - w / 2 + 0.01, cy - 0.001, z0 + 0.01), (w - 0.02, 0, 0), (0, 0, h - 0.02), (0, -1, 0),
                   "Placa_Laboratorio")
    for px in (cx - w / 2 + 0.45, cx + w / 2 - 0.45):
        m.caixa((px - 0.05, cy + 0.08, -0.3), (px + 0.05, cy + 0.18, z0 + h - 0.05), mat="Aco_Preto")
    criar_objeto("PLACA_Laboratorio_de_Engenharia", m, cam)


def vegetacao_fundo(rng):
    cam = "08_Vegetacao_e_Entorno"
    m = Malha("Tronco")
    # pinheiros a esquerda
    for _ in range(9):
        arvore(m, rng.uniform(-9, 9), rng.uniform(8, 17), rng.uniform(10, 14), rng.uniform(2.4, 3.2), rng, "pinheiro")
    for _ in range(4):
        arvore(m, rng.uniform(-16, -9), rng.uniform(-3, 8), rng.uniform(8, 12), rng.uniform(2.2, 3.0), rng, "pinheiro")
    # arvores folhosas ao centro e a direita
    for _ in range(11):
        arvore(m, rng.uniform(10, 34), rng.uniform(10, 22), rng.uniform(6, 9.5), rng.uniform(2.2, 3.4), rng)
    for _ in range(6):
        arvore(m, rng.uniform(36, 56), rng.uniform(11, 24), rng.uniform(5, 8), rng.uniform(2.0, 3.0), rng)
    criar_objeto("ENT_Arvores", m, cam)
    m = Malha("Aco_Galvanizado")
    px, py = 27.5, 11.5
    m.cilindro((px, py, 0), 0.12, 0.07, 8.5, seg=10)
    m.barra((px, py, 8.4), (px - 1.0, py - 0.2, 8.6), 0.06)
    m.caixa((px - 1.4, py - 0.35, 8.5), (px - 0.8, py - 0.05, 8.62), mat="Aco_Preto")
    criar_objeto("ENT_Poste_Iluminacao", m, cam)


def iluminacao_e_cameras():
    cena = bpy.context.scene
    cena.unit_settings.system = "METRIC"
    cena.unit_settings.length_unit = "METERS"
    mundo = bpy.data.worlds.new("Ceu")
    cena.world = mundo
    mundo.use_nodes = True
    nt = mundo.node_tree
    # ceu em degrade (azul profundo no zenite, mais claro no horizonte)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(coord.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], rampa.inputs["Fac"])
    rampa.color_ramp.elements[0].position = 0.0
    rampa.color_ramp.elements[0].color = srgb_linear("#b9d3ec") + [1]
    rampa.color_ramp.elements[1].position = 0.6
    rampa.color_ramp.elements[1].color = srgb_linear("#1554c4") + [1]
    meio = rampa.color_ramp.elements.new(0.1)
    meio.color = srgb_linear("#6fa2e4") + [1]
    nt.links.new(rampa.outputs["Color"], nt.nodes["Background"].inputs["Color"])
    nt.nodes["Background"].inputs["Strength"].default_value = 0.9
    sol_d = bpy.data.lights.new("Sol", "SUN")
    sol_d.energy = 4.2
    sol_d.angle = math.radians(1.2)
    sol_d.color = (1.0, 0.93, 0.82)
    sol = bpy.data.objects.new("Sol", sol_d)
    sol.rotation_euler = (math.radians(62), 0, math.radians(60))
    col = colecao("09_Cameras_e_Luz")
    col.objects.link(sol)

    def camera(nome, loc, alvo, lente):
        cd = bpy.data.cameras.new(nome)
        cd.lens = lente
        cd.clip_end = 1000
        cam = bpy.data.objects.new(nome, cd)
        cam.location = loc
        direcao = Vector(alvo) - Vector(loc)
        cam.rotation_euler = direcao.to_track_quat("-Z", "Y").to_euler()
        col.objects.link(cam)
        return cam
    c1 = camera("Camera_Foto_Fachada", (22.5, -47.0, 4.0), (23.5, 0.0, 8.6), 26)
    camera("Camera_Aerea", (-16.0, -42.0, 30.0), (22.0, -4.0, 0.0), 30)
    camera("Camera_Pergolado", (13.5, -6.0, 1.6), (18.0, 4.0, 1.5), 20)
    camera("Camera_Escada_Salas", (29.5, -9.5, 1.7), (38.5, 0.0, 2.8), 22)
    cena.camera = c1


def montar():
    limpar_cena()
    rng = random.Random(SEMENTE)
    bloco_mecanica(rng)
    pergolado(rng)
    bloco_automacao(rng)
    escada()
    bloco_salas(rng)
    terreno_e_paisagismo(rng)
    placa_principal()
    vegetacao_fundo(rng)
    iluminacao_e_cameras()


# ===========================================================================
# EXPORTACAO / RENDER
# ===========================================================================
def exportar():
    os.makedirs(DIR_SAIDA, exist_ok=True)
    base = os.path.join(DIR_SAIDA, NOME_ARQ)
    bpy.ops.export_scene.gltf(filepath=base + ".glb", export_format="GLB", export_apply=True,
                              export_hierarchy_full_collections=True, export_cameras=False, export_lights=False,
                              export_yup=True)
    os.makedirs(os.path.join(DIR_SAIDA, "fbx"), exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=os.path.join(DIR_SAIDA, "fbx", NOME_ARQ + ".fbx"), path_mode="COPY",
                             embed_textures=True, object_types={"MESH", "EMPTY"}, apply_unit_scale=True)
    os.makedirs(os.path.join(DIR_SAIDA, "obj"), exist_ok=True)
    bpy.ops.wm.obj_export(filepath=os.path.join(DIR_SAIDA, "obj", NOME_ARQ + ".obj"), path_mode="COPY",
                          export_materials=True, export_object_groups=True)
    os.makedirs(os.path.join(DIR_SAIDA, "dae_sketchup"), exist_ok=True)
    bpy.ops.wm.collada_export(filepath=os.path.join(DIR_SAIDA, "dae_sketchup", NOME_ARQ + ".dae"),
                              use_texture_copies=True, triangulate=False)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=base + ".blend", compress=True)
    print("Arquivos exportados em", DIR_SAIDA)


def renderizar(amostras=128):
    cena = bpy.context.scene
    cena.render.engine = "CYCLES"
    cena.cycles.device = "CPU"
    cena.cycles.samples = amostras
    cena.cycles.use_denoising = True
    cena.view_settings.view_transform = "AgX"
    cena.view_settings.look = "AgX - Medium High Contrast"
    cena.render.image_settings.file_format = "PNG"
    for nome, res in (("Camera_Foto_Fachada", (1086, 1448)), ("Camera_Aerea", (1600, 1000)),
                      ("Camera_Pergolado", (1600, 1000)), ("Camera_Escada_Salas", (1600, 1000))):
        cena.camera = bpy.data.objects[nome]
        cena.render.resolution_x, cena.render.resolution_y = res
        cena.render.filepath = os.path.join(DIR_SAIDA, f"render_{nome.lower()}.png")
        bpy.ops.render.render(write_still=True)
    cena.camera = bpy.data.objects["Camera_Foto_Fachada"]


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    montar()
    if bpy.app.background:
        if "--sem-exportar" not in args:
            exportar()
        if "--render" in args:
            amostras = 128
            for a in args:
                if a.startswith("--amostras="):
                    amostras = int(a.split("=")[1])
            renderizar(amostras)
            if "--sem-exportar" not in args:
                bpy.ops.wm.save_as_mainfile(filepath=os.path.join(DIR_SAIDA, NOME_ARQ + ".blend"), compress=True)
        if not os.path.basename(bpy.app.binary_path or "").lower().startswith("blender"):
            # modulo bpy via pip: encerra direto (evita falha na finalizacao do interpretador)
            sys.stdout.flush()
            os._exit(0)
