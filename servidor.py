import asyncio
import datetime
import os
import websockets

CONEXIONES = set()
VERSION_REQUERIDA = "1.0.0"
CLAVE_ADMIN = "Daviconsualiento1414"
soundboard_desactivado = False


async def retransmitir(mensaje, emisor=None):
  """Envía un mensaje a los clientes y limpia automáticamente los desconectados."""
  desconectados = set()
  destino = [c for c in CONEXIONES if c != emisor]

  for c in destino:
    try:
      await c.send(mensaje)
    except Exception:
      desconectados.add(c)

  # Eliminamos los sockets que tiraron error para no saturar la memoria
  for c en desconectados:
    CONEXIONES.discard(c)


async def manejar_cliente(websocket):
  global soundboard_desactivado
  CONEXIONES.add(websocket)
  cliente_verificado = False

  try:
    async for mensaje in websocket:
      # 1. Verificación de versión
      if mensaje.startswith("VER:"):
        version_cliente = mensaje[4:].strip()

        if version_cliente != VERSION_REQUERIDA:
          hora = datetime.datetime.now().strftime("%H:%M")
          msg_aviso = f"TEXT:{hora}|SISTEMA|red|[!] Cliente desactualizado (v{version_cliente}). La versión requerida es v{VERSION_REQUERIDA}."
          try:
            await websocket.send(msg_aviso)
            await websocket.send("DESACTUALIZADO")
            await websocket.close()
          except Exception:
            pass
          return
        else:
          cliente_verificado = True
          estado_sb = "1" if soundboard_desactivado else "0"
          await websocket.send(f"SB_STATE:{estado_sb}")
          continue

      if not cliente_verificado:
        try:
          await websocket.send("DESACTUALIZADO")
          await websocket.close()
        except Exception:
          pass
        return

      # 2. Control Soundboard
      if mensaje.startswith("TOGGLE_SB:"):
        clave_recibida = mensaje[10:]
        if clave_recibida == CLAVE_ADMIN:
          soundboard_desactivado = not soundboard_desactivado
          estado_sb = "1" if soundboard_desactivado else "0"
          estado_txt = (
              "bloqueado" if soundboard_desactivado else "activado"
          )

          hora = datetime.datetime.now().strftime("%H:%M")
          msg_notif = f"TEXT:{hora}|SISTEMA|orange|[!] El Soundboard fue {estado_txt} por un administrador."

          await retransmitir(f"SB_STATE:{estado_sb}")
          await retransmitir(msg_notif)
        else:
          await websocket.send("SB_AUTH_FAILED")
        continue

      # 3. Ignorar audios si está bloqueado
      if mensaje.startswith("SND_KEY:") and soundboard_desactivado:
        continue

      # 4. Retransmisión segura
      await retransmitir(mensaje, emisor=websocket)

  except Exception:
    pass
  finally:
    CONEXIONES.discard(websocket)


async def main():
  puerto = int(os.environ.get("PORT", 10000))

  # ping_interval=20: Envía pings periódicos para mantener el canal abierto en Render
  # ping_timeout=20: Descarta la conexión si el cliente no responde en 20s
  async with websockets.serve(
      manejar_cliente, "0.0.0.0", puerto, ping_interval=20, ping_timeout=20
  ):
    print(f"[+] Servidor activo y blindado en puerto {puerto}")
    await asyncio.Future()


if __name__ == "__main__":
  asyncio.run(main())
