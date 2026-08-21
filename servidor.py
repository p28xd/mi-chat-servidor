import asyncio
import datetime
import os
import websockets

CONEXIONES = set()
VERSION_REQUERIDA = "1.0.0"


async def manejar_cliente(websocket):
  CONEXIONES.add(websocket)
  cliente_verificado = False

  try:
    async for mensaje in websocket:
      # 1. Verificación de versión
      if mensaje.startswith("VER:"):
        version_cliente = mensaje[4:].strip()

        if version_cliente != VERSION_REQUERIDA:
          hora = datetime.datetime.now().strftime("%H:%M")
          msg_aviso = f"TEXT:{hora}|SISTEMA|red|[!] Cliente desactualizado (v{version_cliente}). La version requerida es v{VERSION_REQUERIDA}."

          # Le avisamos por chat y con el flag para que salte el cartel de Tkinter
          await websocket.send(msg_aviso)
          await websocket.send("DESACTUALIZADO")

          # Cierra la conexión inmediatamente
          await websocket.close()
          return
        else:
          cliente_verificado = True
          continue  # No retransmite el comando VER: a los demás

      # 2. Si no es un mensaje "VER:" y el cliente no fue verificado (versión muy vieja)
      if not cliente_verificado:
        hora = datetime.datetime.now().strftime("%H:%M")
        await websocket.send(
            f"TEXT:{hora}|SISTEMA|red|[!] Cliente desactualizado. Por favor reinstalar."
        )
        await websocket.send("DESACTUALIZADO")
        await websocket.close()
        return

      # 3. Retransmite el mensaje a todos los demás clientes
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
