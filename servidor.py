import asyncio
import websockets
import os

CONEXIONES = set()

async def manejar_cliente(websocket):
    CONEXIONES.add(websocket)
    try:
        async for mensaje in websocket:
            # Retransmite el mensaje a todos los demas
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