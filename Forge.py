# Gerador de montanhas
# [02-10][mvfm]
import random

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

class mapa :
    def __init__(self):
        self.dim = 0
        self.matriz = []

    def setDim(self, dim):
        print(f"Dimensões determinadas : {dim}x{dim}")
        self.dim = dim

    def geraMapa(self, geracoes):
        self.matriz = [[setor(i, j) for j in range(self.dim)] for i in range(self.dim)]
        for g in range(geracoes):
            print(f"Geraçao {g+1} de {geracoes}")
            # self.atualizaSetores
        return self.matriz
