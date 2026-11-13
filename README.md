<div align="center">

# CatMouse

**Um jogo de arcade em Python inspirado no clássico Pac-Man.**
Controle um rato, colete queijos e fuja dos gatos pelo labirinto.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Pygame](https://img.shields.io/badge/Pygame-2.x-green)
![License](https://img.shields.io/badge/license-MIT-blue)

</div>

## Recursos

- Labirinto clássico com túnel lateral
- 4 gatos com comportamentos diferentes (perseguidor, emboscador, esperto e distraído)
- Power pellets que invertem a caça
- Queijos bônus que mudam a cada fase
- Pontuação, vidas, fases e recorde salvo
- Sons gerados por código, sem arquivos externos

## Como jogar

```bash
git clone https://github.com/anaelizatx/CatMouse.git
cd CatMouse
pip install -r requirements.txt
python main.py
```

## Controles

| Tecla | Ação |
|-------|------|
| ← ↑ ↓ → / WASD | Mover o rato |
| P | Pausar |
| M | Ligar/desligar som |
| R | Reiniciar |
| ESC | Menu / sair |

## Pontuação

| Item | Pontos |
|------|--------|
| Queijinho | 10 |
| Power pellet | 50 |
| Gato assustado | 200 / 400 / 800 / 1600 |
| Queijo bônus | 100 a 5000 |

## Tecnologias

Python · Pygame

## Autora

Feito por [Ana Eliza](https://github.com/anaelizatx)

## Licença

Distribuído sob a licença MIT.

![Gameplay](docs/gameplay.gif)