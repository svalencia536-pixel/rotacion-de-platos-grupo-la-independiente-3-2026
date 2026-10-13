# -*- coding: utf-8 -*-
"""
Sirve el Dashboard de Ventas de Grupo La Independiente en Railway, SOLO a quien
entre con usuario y clave. Biblioteca estandar de Python, sin dependencias.

Mismo esquema que las fichas tecnicas:

  - Pantalla de ingreso propia y boton "Salir" dentro del dashboard.
  - La sesion viaja en una galleta firmada con HMAC (nadie puede fabricarla),
    HttpOnly y SameSite. Se vence sola (HORAS_SESION, 12 por defecto).
  - La llave de la firma sale de las propias claves: cambiar la clave en
    Railway cierra cualquier sesion abierta.
  - Freno a los intentos a lo bruto: 12 fallos en 10 minutos bloquean esa IP.

USUARIOS: en Railway, pestana Variables. El NOMBRE de la variable es el usuario
y el valor es la clave:

    ADMIN_laindependiente = la-clave

Se pueden crear varios (ADMIN_otro = ...). El usuario no distingue mayusculas;
la clave si. SI NO HAY NINGUN USUARIO, NO SE ENTREGA NADA (responde 503): se
prefiere que la pagina no cargue a que ventas y costos queden abiertos.

Las claves NUNCA van en el repositorio.
"""

import base64
import hashlib
import hmac
import html
import os
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RAIZ = os.path.dirname(os.path.abspath(__file__))
PUERTO = int(os.environ.get("PORT", "8080"))
GALLETA = "sesion_dashboard"
ARCHIVO = "index.html"
LOGO = "data:image/png;base64,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"
ICONO = "data:image/png;base64,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"

try:
    HORAS_SESION = max(1, int(os.environ.get("HORAS_SESION", "12")))
except ValueError:
    HORAS_SESION = 12


def leer_usuarios():
    usuarios = {}
    for nombre, valor in os.environ.items():
        if not nombre.upper().startswith("ADMIN_"):
            continue
        usuario, clave = nombre[6:], (valor or "").strip()
        if usuario and clave:
            usuarios[usuario.upper()] = {"clave": clave, "nombre": usuario}
    return usuarios


USUARIOS = leer_usuarios()


def comprobar(usuario, clave):
    u = (usuario or "").strip().upper().encode("utf-8")
    c = (clave or "").encode("utf-8")
    hallada = None
    for llave, perfil in USUARIOS.items():
        ok_u = hmac.compare_digest(u, llave.encode("utf-8"))
        ok_c = hmac.compare_digest(c, perfil["clave"].encode("utf-8"))
        if ok_u and ok_c:
            hallada = llave
    return hallada


def _secreto():
    material = "|".join(sorted(p["clave"] for p in USUARIOS.values()))
    return hashlib.sha256(("dashboard|" + material).encode("utf-8")).digest()


def firmar_sesion(llave):
    vence = int(time.time()) + HORAS_SESION * 3600
    cuerpo = f"{llave}|{vence}".encode("utf-8")
    firma = hmac.new(_secreto(), cuerpo, hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(cuerpo).decode("ascii").rstrip("=") + "." + firma


def leer_sesion(valor):
    if not valor or "." not in valor:
        return None
    crudo, _, firma = valor.rpartition(".")
    try:
        cuerpo = base64.urlsafe_b64decode(crudo + "=" * (-len(crudo) % 4))
    except Exception:
        return None
    esperada = hmac.new(_secreto(), cuerpo, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(firma, esperada):
        return None
    try:
        llave, _, vence = cuerpo.decode("utf-8").rpartition("|")
        if int(vence) < time.time():
            return None
    except Exception:
        return None
    return USUARIOS.get(llave)


_intentos = {}


def demasiados_intentos(ip):
    fallos = [t for t in _intentos.get(ip, []) if time.time() - t < 600]
    _intentos[ip] = fallos
    return len(fallos) >= 12


def anotar_fallo(ip):
    _intentos.setdefault(ip, []).append(time.time())
    if len(_intentos) > 500:
        for k in [k for k, v in _intentos.items() if not v or time.time() - v[-1] > 600]:
            _intentos.pop(k, None)


_ENTRAR = """<!doctype html>
<meta charset="utf-8">
<title>Dashboard de Ventas · Grupo La Independiente</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<link rel="icon" type="image/png" href="__ICONO__">
<style>
  :root{--fondo:#0d1117;--tarjeta:#161b22;--texto:#e6edf3;--tenue:#8b949e;--linea:#30363d;--acento:#e8394d;--error:#f08076;--bien:#4ea87a}
  *{box-sizing:border-box}
  body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--fondo);
       color:var(--texto);padding:16px;font:15px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
  .caja{width:100%;max-width:380px;background:var(--tarjeta);border:1px solid var(--linea);border-radius:14px;padding:32px 28px}
  .marca{display:flex;align-items:center;gap:12px;margin-bottom:26px}
  .marca{flex-direction:column;text-align:center;gap:10px}.marca img{height:124px;width:auto}
  .marca b{font-size:17px;display:block}
  .marca span{font-size:11px;color:var(--tenue);letter-spacing:.07em;text-transform:uppercase}
  label{display:block;font-size:12.5px;color:var(--tenue);margin:0 0 6px}
  input{width:100%;padding:11px 13px;margin-bottom:16px;font-size:16px;color:var(--texto);background:var(--fondo);
        border:1px solid var(--linea);border-radius:9px}
  input:focus{outline:2px solid var(--acento);outline-offset:-1px;border-color:transparent}
  button{width:100%;padding:12px;font-size:15px;font-weight:600;color:#fff;cursor:pointer;background:var(--acento);border:0;border-radius:9px}
  button:hover{filter:brightness(1.08)}
  .aviso{margin:0 0 18px;padding:10px 13px;border-radius:9px;font-size:13.5px;background:rgba(240,128,118,.12);color:var(--error)}
  .bien{background:rgba(78,168,122,.13);color:var(--bien)}
  .pie{margin:22px 0 0;font-size:12px;color:var(--tenue)}
</style>
<div class="caja">
  <div class="marca"><img src="__LOGO__" alt="Grupo La Independiente">
    <div><b>Dashboard de Ventas</b></div></div>
  __AVISO__
  <form method="post" action="/entrar">
    <label for="u">Usuario</label>
    <input id="u" name="usuario" autocomplete="username" autocapitalize="none" autocorrect="off" spellcheck="false" required autofocus>
    <label for="c">Contrase&ntilde;a</label>
    <input id="c" name="clave" type="password" autocomplete="current-password" required>
    <button type="submit">Entrar</button>
  </form>
  <p class="pie">El usuario no distingue may&uacute;sculas; la contrase&ntilde;a s&iacute;. Si no la tienes, p&iacute;desela al &aacute;rea de costos.</p>
</div>
"""


def pantalla_entrar(aviso="", clase=""):
    html_aviso = f'<p class="aviso {clase}">{html.escape(aviso)}</p>' if aviso else ""
    return (_ENTRAR.replace("__AVISO__", html_aviso).replace("__LOGO__", LOGO)
            .replace("__ICONO__", ICONO)).encode("utf-8")


def boton_salir(perfil):
    quien = html.escape(perfil["nombre"])
    return ("""
<script>
(function(){
  var h = document.querySelector(".header-right");
  if (!h) return;
  var a = document.createElement("a");
  a.href = "/salir";
  a.textContent = "Salir · __QUIEN__";
  a.title = "Cerrar la sesión";
  a.style.cssText = "font-size:.65rem;color:#8b949e;text-decoration:none;border:1px solid #30363d;border-radius:6px;padding:3px 9px;margin-top:4px;display:inline-block";
  h.appendChild(a);
})();
</script>
""").replace("__QUIEN__", quien).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "DashboardLI"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def _responder(self, codigo, cuerpo, tipo="text/plain; charset=utf-8", extra=None):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(cuerpo)

    def _galleta(self, valor, horas):
        partes = [f"{GALLETA}={valor}", "Path=/", "HttpOnly", "SameSite=Lax"]
        if self.headers.get("X-Forwarded-Proto", "").startswith("https"):
            partes.append("Secure")
        partes.append(f"Max-Age={int(horas * 3600)}")
        return "; ".join(partes)

    def _sesion(self):
        for trozo in self.headers.get("Cookie", "").split(";"):
            nombre, _, valor = trozo.strip().partition("=")
            if nombre == GALLETA:
                return leer_sesion(valor)
        return None

    def _sin_configurar(self):
        self._responder(503, (
            "Falta configurar el usuario del dashboard.\n\n"
            "En Railway, pestana Variables, crea una variable cuyo NOMBRE es\n"
            "ADMIN_<usuario> y cuyo VALOR es la clave. Ejemplo:\n\n"
            "    ADMIN_laindependiente = la clave\n\n"
            "Hasta entonces el dashboard no se entrega.\n").encode("utf-8"))

    def do_GET(self):
        if not USUARIOS:
            return self._sin_configurar()
        camino = urllib.parse.urlparse(self.path).path
        if camino == "/favicon.ico":
            return self._responder(200, base64.b64decode(ICONO.split(",", 1)[1]), "image/png")
        if camino == "/salir":
            return self._responder(200, pantalla_entrar("Saliste del dashboard.", "bien"),
                                   "text/html; charset=utf-8",
                                   {"Set-Cookie": self._galleta("", 0)})
        perfil = self._sesion()
        if not perfil:
            return self._responder(200, pantalla_entrar(), "text/html; charset=utf-8")
        with open(os.path.join(RAIZ, ARCHIVO), "rb") as fh:
            cuerpo = fh.read() + boton_salir(perfil)
        return self._responder(200, cuerpo, "text/html; charset=utf-8")

    do_HEAD = do_GET

    def do_POST(self):
        if not USUARIOS:
            return self._sin_configurar()
        if urllib.parse.urlparse(self.path).path != "/entrar":
            return self._responder(404, b"No existe.\n")
        ip = self.headers.get("X-Forwarded-For", "").split(",")[0].strip() or self.address_string()
        if demasiados_intentos(ip):
            return self._responder(429, pantalla_entrar("Demasiados intentos fallidos. Espera unos minutos."),
                                   "text/html; charset=utf-8")
        try:
            largo = min(int(self.headers.get("Content-Length", "0")), 8192)
        except ValueError:
            largo = 0
        campos = urllib.parse.parse_qs(self.rfile.read(largo).decode("utf-8", "replace"))
        llave = comprobar((campos.get("usuario") or [""])[0], (campos.get("clave") or [""])[0])
        if not llave:
            anotar_fallo(ip)
            return self._responder(401, pantalla_entrar("Usuario o contraseña incorrectos."),
                                   "text/html; charset=utf-8")
        return self._responder(303, b"", extra={
            "Location": "/",
            "Set-Cookie": self._galleta(firmar_sesion(llave), HORAS_SESION)})

    def log_message(self, formato, *args):
        sys.stdout.write("%s - %s\n" % (self.address_string(), formato % args))
        sys.stdout.flush()


if __name__ == "__main__":
    if not USUARIOS:
        print("ATENCION: no hay ningun usuario ADMIN_<usuario>. El dashboard respondera 503.", flush=True)
    else:
        print("Usuarios configurados: " + ", ".join(p["nombre"] for p in USUARIOS.values()), flush=True)
    print(f"Dashboard en el puerto {PUERTO}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PUERTO), Handler).serve_forever()
