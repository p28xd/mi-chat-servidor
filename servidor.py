import asyncio
import datetime
import os
import websockets

CONEXIONES = set()
VERSION_REQUERIDA = "1.0.0"


async def manejar_cliente(websocket):
  CONEXIONES.add(websocket)
  try:
    async for mensaje in websocket:
      # Verificación de versión al conectar
      if mensaje.startswith("VER:"):
        version_cliente = mensaje[4:].strip()
        if version_cliente != VERSION_REQUERIDA:
          hora = datetime.datetime.now().strftime("%H:%M")
          # Se le envía SOLO a este cliente
          msg_aviso = (
              f"TEXT:{hora}|SISTEMA|red|[!] Cliente desactualizado"
              f" (v{version_cliente}). La version requerida es"
              f" v{VERSION_REQUERIDA}."
          )
          await websocket.send(msg_aviso)
        continue  # Evita retransmitir el paquete "VER:" a los demás

      # Retransmite el mensaje a todos los demás
      para_enviar = [c for c in CONEXIONES if c != websocket]
      if para_enviar:
        await asyncio.gather(*[c.send(mensaje) for c in para_enviar])
  except:
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
