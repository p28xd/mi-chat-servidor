import asyncio
import datetime
import os
import websockets

CONEXIONES = {}  # Ahora guarda {websocket: apodo}
VERSION_REQUERIDA = "1.1.0"
CLAVE_ADMIN = os.environ.get("CLAVE_ADMIN", "Daviconsualiento1414")
soundboard_desactivado = False


async def enviar_directo(cliente, mensaje):
  try:
    await asyncio.wait_for(cliente.send(mensaje), timeout=1.0)
  except Exception:
    if cliente in CONEXIONES:
      del CONEXIONES[cliente]


async def retransmitir(mensaje, emisor=None):
  destinatarios = [c for c in CONEXIONES.keys() if c != emisor]
  for cliente in destinatarios:
    asyncio.create_task(enviar_directo(cliente, mensaje))


async def retransmitir_lista_usuarios():
  """Envía la lista actualizada de conectados a todos."""
  lista = ",".join([apodo for apodo in CONEXIONES.values() if apodo])
  await retransmitir(f"USER_LIST:{lista}")


async def manejar_cliente(websocket):
  global soundboard_desactivado
  CONEXIONES[websocket] = ""  # Se conecta sin apodo asignado aún
  cliente_verificado = False

  try:
    async for mensaje in websocket:
      # Verificación de versión
      if mensaje.startswith("VER:"):
        version_cliente = mensaje[4:].strip()
        if version_cliente != VERSION_REQUERIDA:
          hora = datetime.datetime.now().strftime("%H:%M")
          msg_aviso = f"TEXT:{hora}|SISTEMA|red|[!] Cliente desactualizado (v{version_cliente}). Requerida v{VERSION_REQUERIDA}."
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

      # Registro de usuario (para la lista de Tab)
      if mensaje.startswith("JOIN:"):
        apodo = mensaje[5:].strip()
        CONEXIONES[websocket] = apodo
        await retransmitir_lista_usuarios()
        continue

      # Control Soundboard
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

      # Ignorar audios si está bloqueado
      if mensaje.startswith("SND_KEY:") and soundboard_desactivado:
        continue

      # Retransmisión normal
      await retransmitir(mensaje, emisor=websocket)

  except Exception:
    pass
  finally:
    if websocket in CONEXIONES:
      del CONEXIONES[websocket]
      await retransmitir_lista_usuarios()


async def main():
  puerto = int(os.environ.get("PORT", 10000))
  async with websockets.serve(
      manejar_cliente, "0.0.0.0", puerto, ping_interval=20, ping_timeout=20
  ):
    print(f"[+] Servidor activo en puerto {puerto}")
    await asyncio.Future()


if __name__ == "__main__":
  asyncio.run(main())
