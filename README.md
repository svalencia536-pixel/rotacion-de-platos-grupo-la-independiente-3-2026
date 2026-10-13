# Dashboard de Ventas · Grupo La Independiente

Dashboard de ventas (enero–septiembre 2026) con cuatro paneles: Resumen por
Subcategoría, Top 20 Rotación, Tendencia e Ingeniería de Menú.

## Acceso con usuario y clave

Lo sirve `servidor.py` (Python, solo biblioteca estándar). Sin sesión no se
entrega nada: ni ventas ni costos.

En Railway, pestaña **Variables**: el NOMBRE de la variable es el usuario y el
valor es la clave.

| Variable | Qué es |
|---|---|
| `ADMIN_<usuario>` | Usuario y clave de acceso (ej. `ADMIN_laindependiente`) |
| `HORAS_SESION` | Opcional. Horas que dura la sesión (12 por defecto) |

Cambiar la clave en Railway cierra cualquier sesión abierta. Las claves nunca
van en el repositorio.

## Actualizar los datos

Los datos van dentro de `index.html`. Para un mes nuevo se reemplaza ese
archivo; Railway lo vuelve a publicar solo.
