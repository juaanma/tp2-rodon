# Datos

## Procedencia
Todos los datos de este trabajo son sintéticos. Los escenarios (probabilidades
de convertir un penal, repeticiones y semilla) fueron inventados por el autor
para ilustrar el funcionamiento del programa y no representan estadísticas
reales de ningún equipo ni jugador.

Autor: Juan Manuel Rodon. Fecha de creación: 22/10/2026.

## Unidad de análisis
Cada fila de los archivos de escenarios es un escenario de simulación.

## Variables
- id: identificador del escenario, formato ESC-001
- prob_gol_a: probabilidad (0 a 1) de que el equipo A convierta un penal
- prob_gol_b: probabilidad (0 a 1) de que el equipo B convierta un penal
- repeticiones: cantidad de tandas a simular
- semilla: número entero para reproducir los resultados

## Limitaciones
- Las probabilidades son supuestas, por lo que los resultados solo valen
  para esos supuestos.
- Se asume que cada penal es independiente y que todos los pateadores de un
  equipo tienen la misma probabilidad de convertir.