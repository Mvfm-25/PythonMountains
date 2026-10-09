#!/usr/bin/env python3
# Visualizador do mapa de alturas [versão Linux / Arch]
# Uso : ./Okulus.py [-s subdivisoes] [-d tamanho] [-g geracoes] [-r semente]
# Dependências : sudo pacman -S glfw python-opengl glu freeglut
#                pyGLFW não está nos repositórios oficiais : usar um venv
#                python -m venv --system-site-packages .venv && .venv/bin/pip install glfw
# Wayland & X11 : o backend segue XDG_SESSION_TYPE; para forçar o X11 (XWayland),
#                 rodar com XDG_SESSION_TYPE=x11
#                 o freeglut (texto da pergunta de salvar) só fala X11 : sem ele ou sem
#                 XWayland, a pergunta aparece no título da janela & no terminal
# Setas / arrastar o mouse : orbita | Z / X / scroll : aproxima / afasta
# W : wireframe | C : alterna cores (altura / roleta) | L : liga / desliga a luz | R : novo mapa | ESC : sai
# Ao sair, pergunta na tela "Salvar terreno? S/N" (ESC cancela) e salva como PlanoNN.obj
import math
import os
import glfw
from OpenGL.GL import *
from OpenGL.GLU import gluPerspective, gluLookAt
from OpenGL.GLUT import glutInit, glutBitmapString, glutBitmapWidth, GLUT_BITMAP_HELVETICA_18
import Forge

# Altura máxima do relevo, como fração do lado do plano
ESCALA_ALTURA = 0.25

PERGUNTA_SALVAR = b"Salvar terreno? S/N"

# Velocidades da câmera no teclado : graus por segundo & fator de zoom por segundo
VELOCIDADE_GIRO = 90.0
VELOCIDADE_ZOOM = 1.5

# Luz direcional fixa no mundo (w = 0), vinda do alto & de lado para marcar as encostas
DIRECAO_LUZ = (-0.6, 1.0, 0.4, 0.0)
LUZ_AMBIENTE = (0.30, 0.30, 0.30, 1.0)
LUZ_DIFUSA = (0.85, 0.85, 0.85, 1.0)

# (altura, (r, g, b)), do vale ao pico
CORES = [
    (0.0, (0.13, 0.37, 0.18)),
    (0.5, (0.45, 0.36, 0.24)),
    (0.8, (0.55, 0.55, 0.55)),
    (1.0, (1.00, 1.00, 1.00)),
]

# Roleta de cores distintas : 9 cores em um bloco 3x3, para nenhum setor
# ter a mesma cor de qualquer um dos seus 8 vizinhos (inclusive diagonais)
ROLETA = [
    (0.90, 0.20, 0.20), (0.95, 0.60, 0.10), (0.95, 0.90, 0.20),
    (0.30, 0.80, 0.25), (0.15, 0.70, 0.75), (0.20, 0.35, 0.90),
    (0.60, 0.25, 0.85), (0.95, 0.45, 0.70), (0.55, 0.35, 0.20),
]

def corRoleta(s):
    return ROLETA[(s.x % 3) * 3 + s.z % 3]

def corAltura(y):
    for (y0, c0), (y1, c1) in zip(CORES, CORES[1:]):
        if y <= y1:
            t = (y - y0) / (y1 - y0)
            return tuple(a + (b - a) * t for a, b in zip(c0, c1))
    return CORES[-1][1]

# Normal unitária do triângulo, sempre apontando para cima (y > 0)
def normalTriangulo(p0, p1, p2):
    ux, uy, uz = (p1[k] - p0[k] for k in range(3))
    vx, vy, vz = (p2[k] - p0[k] for k in range(3))
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    if ny < 0:
        nx, ny, nz = -nx, -ny, -nz
    comprimento = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / comprimento, ny / comprimento, nz / comprimento

class okulus :
    def __init__(self, mapa, geracoes):
        self.mapa = mapa
        self.geracoes = geracoes
        self.janela = None
        self.lista = None
        self.wireframe = False
        self.roleta = False
        self.iluminacao = True
        # Pergunta de salvar aberta na tela, esperando S / N
        self.perguntando = False
        # Câmera orbital, em graus
        self.giro = 45.0
        self.inclinacao = 35.0
        self.distancia = mapa.lado() * 1.6
        self.mouseAnterior = None

    def abreJanela(self, largura, altura):
        if not glfw.init():
            raise RuntimeError("Não foi possível iniciar o GLFW")
        # Identificam a janela para o gerenciador : app_id no Wayland, WM_CLASS no X11
        glfw.window_hint_string(glfw.WAYLAND_APP_ID, "okulus")
        glfw.window_hint_string(glfw.X11_CLASS_NAME, "okulus")
        glfw.window_hint_string(glfw.X11_INSTANCE_NAME, "okulus")
        self.janela = glfw.create_window(largura, altura, "Okulus", None, None)
        if not self.janela:
            glfw.terminate()
            raise RuntimeError("Não foi possível criar a janela")
        glfw.make_context_current(self.janela)
        glfw.swap_interval(1)
        glfw.set_key_callback(self.janela, self.aoTeclar)
        glfw.set_cursor_pos_callback(self.janela, self.aoMoverMouse)
        glfw.set_scroll_callback(self.janela, self.aoRolar)
        glfw.set_window_close_callback(self.janela, self.aoFechar)
        # O freeglut do Arch só fala X11 : sem DISPLAY (Wayland sem XWayland) o glutInit derruba o processo
        # bool(glutInit) é falso quando o freeglut não está instalado
        self.glut = bool(glutInit) and bool(os.environ.get("DISPLAY"))
        if self.glut:
            glutInit()
        glEnable(GL_DEPTH_TEST)
        glShadeModel(GL_FLAT)
        glClearColor(0.08, 0.09, 0.12, 1.0)
        # A cor de cada triângulo (glColor) vira o material iluminado
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_AMBIENT, LUZ_AMBIENTE)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, LUZ_DIFUSA)
        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.0, 0.0, 0.0, 1.0))
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glEnable(GL_COLOR_MATERIAL)

    # Monta a malha uma vez só; cada quadrado entre 4 setores vira 2 triângulos
    # Na roleta, o quadrado inteiro leva a cor do setor no seu canto (i, j)
    # Cada triângulo leva a sua normal, para a luz marcar o relevo
    def compilaMalha(self):
        matriz = self.mapa.matriz
        dim = self.mapa.dim
        escala = self.mapa.lado() * ESCALA_ALTURA
        if self.lista is not None:
            glDeleteLists(self.lista, 1)
        self.lista = glGenLists(1)
        glNewList(self.lista, GL_COMPILE)
        glBegin(GL_TRIANGLES)
        for i in range(dim - 1):
            for j in range(dim - 1):
                a, b = matriz[i][j], matriz[i + 1][j]
                c, d = matriz[i + 1][j + 1], matriz[i][j + 1]
                for triangulo in ((a, b, c), (a, c, d)):
                    if self.roleta:
                        glColor3f(*corRoleta(a))
                    else:
                        glColor3f(*corAltura(sum(s.y for s in triangulo) / 3))
                    vertices = [self.mapa.coordenadas(s, escala) for s in triangulo]
                    glNormal3f(*normalTriangulo(*vertices))
                    for v in vertices:
                        glVertex3f(*v)
        glEnd()
        glEndList()

    def desenha(self):
        largura, altura = glfw.get_framebuffer_size(self.janela)
        glViewport(0, 0, largura, altura)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, largura / max(altura, 1), 0.1, self.mapa.lado() * 20)

        giro = math.radians(self.giro)
        inclinacao = math.radians(self.inclinacao)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(self.distancia * math.cos(inclinacao) * math.sin(giro),
                  self.distancia * math.sin(inclinacao),
                  self.distancia * math.cos(inclinacao) * math.cos(giro),
                  0, 0, 0,
                  0, 1, 0)

        # Posição da luz dada depois da câmera, para ela ficar presa ao mundo e não à câmera
        glLightfv(GL_LIGHT0, GL_POSITION, DIRECAO_LUZ)
        if self.iluminacao:
            glEnable(GL_LIGHTING)
        else:
            glDisable(GL_LIGHTING)

        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE if self.wireframe else GL_FILL)
        glCallList(self.lista)

        if self.perguntando:
            self.desenhaPergunta(largura, altura)

    # Abre / fecha a pergunta de salvar; sem GLUT, ela vai para o título da janela & o terminal
    def pergunta(self, aberta):
        self.perguntando = aberta
        if not self.glut:
            texto = PERGUNTA_SALVAR.decode()
            glfw.set_window_title(self.janela, f"Okulus : {texto}" if aberta else "Okulus")
            if aberta:
                print(f"{texto} (ESC cancela)")

    # Caixa semitransparente no centro da tela, por cima do terreno
    def desenhaPergunta(self, largura, altura):
        if not self.glut:
            return
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, largura, 0, altura, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        larguraTexto = sum(glutBitmapWidth(GLUT_BITMAP_HELVETICA_18, c) for c in PERGUNTA_SALVAR)
        x, y = (largura - larguraTexto) / 2, altura / 2
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(0.0, 0.0, 0.0, 0.75)
        glRectf(x - 24, y - 20, x + larguraTexto + 24, y + 32)
        glDisable(GL_BLEND)

        glColor3f(1.0, 1.0, 1.0)
        glRasterPos2f(x, y)
        glutBitmapString(GLUT_BITMAP_HELVETICA_18, PERGUNTA_SALVAR)
        glEnable(GL_DEPTH_TEST)

    def salvaTerreno(self):
        nome = Forge.proximoNomeOBJ()
        self.mapa.exportaOBJ(nome, self.mapa.lado() * ESCALA_ALTURA)

    # Botão de fechar da janela : em vez de sair, abre a pergunta
    def aoFechar(self, janela):
        if not self.perguntando:
            glfw.set_window_should_close(janela, False)
            self.pergunta(True)

    def aoTeclar(self, janela, tecla, scancode, acao, mods):
        if acao != glfw.PRESS:
            return
        if self.perguntando:
            if tecla == glfw.KEY_S:
                self.salvaTerreno()
                glfw.set_window_should_close(janela, True)
            elif tecla == glfw.KEY_N:
                glfw.set_window_should_close(janela, True)
            elif tecla == glfw.KEY_ESCAPE:
                self.pergunta(False)
            return
        if tecla == glfw.KEY_ESCAPE:
            self.pergunta(True)
        elif tecla == glfw.KEY_W:
            self.wireframe = not self.wireframe
        elif tecla == glfw.KEY_C:
            self.roleta = not self.roleta
            self.compilaMalha()
        elif tecla == glfw.KEY_L:
            self.iluminacao = not self.iluminacao
        elif tecla == glfw.KEY_R:
            self.mapa.geraMapa(self.geracoes)
            self.compilaMalha()

    def aoMoverMouse(self, janela, x, y):
        if glfw.get_mouse_button(janela, glfw.MOUSE_BUTTON_LEFT) == glfw.PRESS and self.mouseAnterior:
            self.giro -= (x - self.mouseAnterior[0]) * 0.4
            self.inclinacao += (y - self.mouseAnterior[1]) * 0.4
            self.inclinacao = max(5.0, min(89.0, self.inclinacao))
        self.mouseAnterior = (x, y)

    def aoRolar(self, janela, dx, dy):
        self.aplicaZoom(0.9 ** dy)

    def aplicaZoom(self, fator):
        self.distancia = max(self.mapa.lado() * 0.3, min(self.mapa.lado() * 10, self.distancia * fator))

    # Teclas seguradas : lidas a cada quadro para o movimento ser contínuo
    def moveCamera(self, dt):
        def apertada(tecla):
            return glfw.get_key(self.janela, tecla) == glfw.PRESS

        if apertada(glfw.KEY_LEFT):
            self.giro -= VELOCIDADE_GIRO * dt
        if apertada(glfw.KEY_RIGHT):
            self.giro += VELOCIDADE_GIRO * dt
        if apertada(glfw.KEY_UP):
            self.inclinacao += VELOCIDADE_GIRO * dt
        if apertada(glfw.KEY_DOWN):
            self.inclinacao -= VELOCIDADE_GIRO * dt
        self.inclinacao = max(5.0, min(89.0, self.inclinacao))

        if apertada(glfw.KEY_Z):
            self.aplicaZoom(VELOCIDADE_ZOOM ** -dt)
        if apertada(glfw.KEY_X):
            self.aplicaZoom(VELOCIDADE_ZOOM ** dt)

    def roda(self, largura=1024, altura=768):
        self.abreJanela(largura, altura)
        self.compilaMalha()
        anterior = glfw.get_time()
        while not glfw.window_should_close(self.janela):
            agora = glfw.get_time()
            self.moveCamera(agora - anterior)
            anterior = agora
            self.desenha()
            glfw.swap_buffers(self.janela)
            glfw.poll_events()
        glfw.terminate()

if __name__ == "__main__":
    args = Forge.leParametros("Visualizador do mapa de alturas")

    m = Forge.mapa()
    m.setDim(args.subdivisoes)
    m.setTamanho(args.tamanho)
    m.geraMapa(args.geracoes, args.semente)
    okulus(m, args.geracoes).roda()
