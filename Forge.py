# Gerador de montanhas
# [02-10][mvfm]
import argparse
import os
import random

# Padrões da linha de comando
SUBDIVISOES_PADRAO = 32
GERACOES_PADRAO = 1

# Menor altura de pico possível após a normalização; o pico de cada mapa é sorteado entre isso & 1
AMPLITUDE_MINIMA = 0.4

class setor :
    def __init__(self, x, z):
        self.x = x
        # Float entre 0 & 1
        self.y = random.random()
        self.z = z

    def atualizaAltura(self, novaAltura):
        print(f"Setor atualizado : ({self.x}, {self.z})")
        print(f"Indo de {self.y} de altura para {novaAltura}")
        self.y = novaAltura

    def mediaVizinhos(self, matriz):
        soma = 0.0
        encontros = 0

        for dx in [-1, 0, 1]:
            for dz in [-1, 0, 1]:

                # Ignora próprio setor
                if(dx == 0 and dz == 0):
                    continue

                nx = self.x + dx
                nz = self.z + dz

                # Verifica se não passamos dos limites da matriz
                if(0 <= nx < len(matriz) and 0 <= nz < len(matriz[0])):
                    encontros += 1
                    soma += matriz[nx][nz].y

        return soma / encontros if encontros else self.y


class mapa :
    def __init__(self):
        self.dim = 0
        self.matriz = []
        self.semente = None

    def setDim(self, dim):
        print(f"Dimensões determinadas : {dim}x{dim}")
        self.dim = dim

    def atualizaSetores(self):
        # 1ª passada : calcula todas as médias com as alturas ainda intactas
        medias = [[s.mediaVizinhos(self.matriz) for s in linha] for linha in self.matriz]

        # 2ª passada : só então aplica as novas alturas
        for linha, mediasLinha in zip(self.matriz, medias):
            for s, media in zip(linha, mediasLinha):
                s.y = media

    # Estica as alturas de volta para [0, amplitude], com amplitude sorteada entre os mapas
    def normalizaAlturas(self):
        alturas = [s.y for linha in self.matriz for s in linha]
        menor, maior = min(alturas), max(alturas)
        faixa = maior - menor
        amplitude = random.uniform(AMPLITUDE_MINIMA, 1.0)
        print(f"Normalizando : [{menor:.3f}, {maior:.3f}] -> [0, {amplitude:.3f}]")

        for linha in self.matriz:
            for s in linha:
                # Mapa completamente plano : não há o que esticar
                s.y = (s.y - menor) / faixa * amplitude if faixa else 0.0

    # Sem semente, sorteia uma nova fora do gerador do mapa, para o "R" do Okulus não repetir mapas
    def geraMapa(self, geracoes, semente=None):
        if semente is None:
            semente = random.SystemRandom().randrange(2**31)
        self.semente = semente
        random.seed(semente)
        print(f"Semente : {semente}")
        self.matriz = [[setor(i, j) for j in range(self.dim)] for i in range(self.dim)]
        for g in range(geracoes):
            print(f"Geraçao {g+1} de {geracoes}")
            self.atualizaSetores()
        self.normalizaAlturas()
        return self.matriz

    # Salva a malha como .obj : um vértice por setor & 2 triângulos por quadrado, como no Okulus
    # Faces em sentido anti-horário visto de cima, para a normal apontar para o céu
    def exportaOBJ(self, caminho, escalaAltura=1.0):
        centro = (self.dim - 1) / 2
        indice = lambda i, j: i * self.dim + j + 1
        with open(caminho, "w", encoding="utf-8") as arquivo:
            arquivo.write(f"# PythonMountains : {self.dim}x{self.dim}, semente {self.semente}\n")
            for linha in self.matriz:
                for s in linha:
                    arquivo.write(f"v {s.x - centro} {s.y * escalaAltura:.6f} {s.z - centro}\n")
            for i in range(self.dim - 1):
                for j in range(self.dim - 1):
                    a, b = indice(i, j), indice(i + 1, j)
                    c, d = indice(i + 1, j + 1), indice(i, j + 1)
                    arquivo.write(f"f {a} {c} {b}\nf {a} {d} {c}\n")
        print(f"Terreno salvo em {caminho}")


# Próximo nome livre na pasta atual : Plano01.obj, Plano02.obj...
def proximoNomeOBJ(prefixo="Plano"):
    n = 1
    while os.path.exists(f"{prefixo}{n:02d}.obj"):
        n += 1
    return f"{prefixo}{n:02d}.obj"


# Semente pode ser qualquer texto; números viram int, para "-r 12345" repetir a semente sorteada 12345
def leSemente(texto):
    try:
        return int(texto)
    except ValueError:
        return texto

# Parâmetros de linha de comando compartilhados : -s subdivisões, -g gerações & -r semente
def leParametros(descricao):
    parser = argparse.ArgumentParser(description=descricao)
    parser.add_argument("-s", "--subdivisoes", type=int, default=SUBDIVISOES_PADRAO,
                        help=f"setores por lado do plano (padrão : {SUBDIVISOES_PADRAO})")
    parser.add_argument("-g", "--geracoes", type=int, default=GERACOES_PADRAO,
                        help=f"quantas gerações de regras aplicar (padrão : {GERACOES_PADRAO})")
    parser.add_argument("-r", "--semente", type=leSemente, default=None,
                        help="semente do gerador, número ou texto, para repetir um mapa (padrão : sorteada)")
    args = parser.parse_args()
    if args.subdivisoes < 2:
        parser.error("subdivisoes precisa ser pelo menos 2")
    if args.geracoes < 0:
        parser.error("geracoes não pode ser negativo")
    return args

if __name__ == "__main__":
    args = leParametros("Gerador de montanhas")
    m = mapa()
    m.setDim(args.subdivisoes)
    m.geraMapa(args.geracoes, args.semente)
