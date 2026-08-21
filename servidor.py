import asyncio
import datetime
import os
import websockets

CONEXIONES = set()
VERSION_REQUERIDA = "1.0.0"
CLAVE_ADMIN = "Daviconsualiento1414"

# Estado global del soundboard para todos los usuarios
soundboard_desactivado = False


async def manejar_cliente(websocket):
  global soundboard_desactivado
  CONEXIONES.add(websocket)
  cliente_verificado = False

  try:
    async for mensaje in websocket:
      # 1. Verificación de versión al conectar
      if mensaje.startswith("VER:"):
        version_cliente = mensaje[4:].strip()

        if version_cliente != VERSION_REQUERIDA:
          hora = datetime.datetime.now().strftime("%H:%M")
          msg_aviso = f"TEXT:{hora}|SISTEMA|red|[!] Cliente desactualizado (v{version_cliente}). La version requerida es v{VERSION_REQUERIDA}."
          await websocket.send(msg_aviso)
          await websocket.send("DESACTUALIZADO")
          await websocket.close()
          return
        else:
          cliente_verificado = True
          # Le mandamos al cliente nuevo el estado actual del soundboard
          estado_sb = "1" if soundboard_desactivado else "0"
          await websocket.send(f"SB_STATE:{estado_sb}")
          continue

      if not cliente_verificado:
        hora = datetime.datetime.now().strftime("%H:%M")
        await websocket.send(
            f"TEXT:{hora}|SISTEMA|red|[!] Cliente antiguo sin verificacion."
        )
        await websocket.send("DESACTUALIZADO")
        await websocket.close()
        return

      # 2. Control del Soundboard con contraseña
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

          # Notificamos el nuevo estado a ABSOLUTAMENTE TODOS los conectados
          for c in list(CONEXIONES):
            try:
              await c.send(f"SB_STATE:{estado_sb}")
              await c.send(msg_notif)
            except Exception:
              pass
        else:
          # Si le erró a la clave, le avisamos solo al que la ingresó
          await websocket.send("SB_AUTH_FAILED")
        continue

      # 3. Si el soundboard está desactivado globalmente, ignora solicitudes de audio
      if mensaje.startswith("SND_KEY:") and soundboard_desactivado:
        continue

      # 4. Retransmisión normal (dibujo, chat, audios) a los demás
      para_enviar = [c for c in CONEXIONES if c != websocket]
      if para_enviar:
        await asyncio.gather(*[c.send(mensaje) for c in para_enviar])

  except Exception:
    pass
  finally:
    if websocket in CONEXIONES:
      CONEXIONES.remove(websocket)


async def main():
  puerto = int(os.environ.get("PORT", 10000))
  async with websockets.serve(manejar_cliente, "0.0.0.0", puerto):
    print(f"[+] Servidor activo en puerto {puerto}")
    await asyncio.Future()


if __name__ == "__main__":
  asyncio.run(main())
