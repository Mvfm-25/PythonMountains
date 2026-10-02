# Gerador de montanhas
# [02-10][mvfm]
import random

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

    def geraMapa(self, geracoes):
        self.matriz = [[setor(i, j) for j in range(self.dim)] for i in range(self.dim)]
        for g in range(geracoes):
            print(f"Geraçao {g+1} de {geracoes}")
            self.atualizaSetores()
        self.normalizaAlturas()
        return self.matriz
