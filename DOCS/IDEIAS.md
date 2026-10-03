# Ideias para o gerador de terreno

Hoje o algoritmo sorteia um ruído aleatório em cada setor, suaviza várias vezes pela média dos 8 vizinhos e depois normaliza. O resultado são colinas arredondadas de um tamanho só: cada geração deixa o terreno mais liso e mais baixo, e a normalização compensa a perda de altura. Por isso, quase tudo que vale a pena adicionar serve para criar **detalhe em várias escalas** e **formas mais naturais**.

## Melhorias rápidas

1. **Semente (`-r --semente`)**: passar uma seed para `random.seed()` deixa os mapas reproduzíveis, o que ajuda a comparar o efeito de cada regra nova no mesmo terreno.
2. **Iluminação no Okulus**: hoje não há luz, só cor por altura, e o relevo fica difícil de ler. Calcular a normal de cada triângulo e ligar `GL_LIGHTING` muda muito a visualização.
3. **Redistribuição de altura**: aplicar `y = y ** expoente` depois da normalização. Com expoente > 1 os vales ficam planos e os picos agudos, que é a cara de uma cordilheira.
4. **Nível do mar**: tudo abaixo de um limiar vira água, com uma cor azul e altura achatada. Dá para controlar por um parâmetro como `-a`.

## Novas regras de geração

5. **Ruído em oitavas (fBm)**: somar camadas de ruído em escalas diferentes. Uma grade grossa com amplitude grande dá as montanhas, e grades cada vez mais finas com amplitude menor dão os detalhes. É a técnica padrão, e pode usar Perlin/Simplex ou ser feita com o sistema atual de "sortear e suavizar" em resoluções diferentes.
6. **Diamond-square**: subdivide o plano recursivamente e desloca o ponto médio com um ruído que diminui a cada nível. Combina com a ideia de "subdivisões", mas exige tamanho 2ⁿ+1.
7. **Ruído "ridged"**: `1 - |ruído|` cria cristas finas e afiadas, como as de montanhas reais.
8. **Máscara de ilha**: multiplica a altura por um fator que cai com a distância ao centro, para o mapa terminar no mar em vez de cortado na borda.

## Erosão

O sistema já é um autômato celular (regras aplicadas por gerações), então a erosão se encaixa bem nele.

9. **Erosão térmica**: se a diferença de altura para um vizinho passa de um ângulo limite, parte do material escorre para ele. Isso forma encostas com rampas de detritos e é simples de escrever como uma regra nova em `atualizaSetores`.
10. **Erosão hidráulica**: simula gotas de chuva que descem a encosta, carregam sedimento e o depositam mais abaixo. É a que mais aumenta o realismo, porque cava vales e cria redes de drenagem, mas também é a mais trabalhosa.

## Cor e biomas

11. **Cor pela inclinação**: setores muito inclinados ficam cor de rocha, mesmo em altitude baixa, e a neve só fica onde o terreno é mais plano.
12. **Mapa de umidade**: um segundo ruído que, junto com a altura, define o bioma (deserto, floresta, tundra).

## Infraestrutura

13. **NumPy**: guardar as alturas num `ndarray` em vez de uma matriz de objetos `setor`. A média dos vizinhos vira uma convolução vetorizada, e com `-s 500` a diferença é de minutos para frações de segundo. Isso fica importante quando entrar a erosão.
14. **Exportação**: salvar o heightmap como PNG em tons de cinza ou a malha como `.obj`, para abrir no Blender ou numa engine.

## Ordem sugerida

1. **Semente** e **iluminação**: rápidas, e ajudam a avaliar todo o resto.
2. **Ruído em oitavas**: o maior ganho visual.
3. **Erosão térmica**: como nova regra de geração.
4. **NumPy**: antes da erosão hidráulica, se o tamanho dos mapas começar a pesar.
