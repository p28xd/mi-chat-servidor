import asyncio
import os
import websockets

# Definimos la versión mínima y la clave del admin del lado del servidor
VERSION_MINIMA = "1.1.0"
CLAVE_ADMIN = "Daviconsualiento1414"  # Acá cambiás la clave por la que quieras

CLIENTES = set()
soundboard_bloqueado = False

async def handler(websocket):
    global soundboard_bloqueado
    CLIENTES.add(websocket)
    apodo_usuario = "Anónimo"

    try:
        async for message in websocket:
            # 1. VALIDACIÓN DE VERSIÓN Y REGISTRO AL INICIAR
            if message.startswith("INIT:"):
                partes = message[5:].split("|", 1)
                version_cli = partes[0]
                apodo_usuario = partes[1] if len(partes) > 1 else "Anónimo"

                # Si la versión es vieja, lo rebotamos inmediatamente
                if version_cli < VERSION_MINIMA:
                    await websocket.send("ERR_VER:Tu cliente está desactualizado (v" + version_cli + "). La versión mínima requerida es v" + VERSION_MINIMA + ".")
                    await websocket.close()
                    return
                else:
                    # Notificamos a todos que entró alguien nuevo
                    import datetime
                    hora = datetime.datetime.now().strftime("%H:%M")
                    msg_sistema = f"TEXT:{hora}|SISTEMA|#27ae60|🟢 {apodo_usuario} se unió al chat.|NONE"
                    for c in CLIENTES:
                        if c.open:
                            await c.send(msg_sistema)

                    # Si el soundboard ya estaba bloqueado, le avisamos al nuevo cliente
                    if soundboard_bloqueado:
                        await websocket.send("SB_STATE:LOCKED")

            # 2. VALIDACIÓN DE ADMIN PARA EL SOUNDBOARD
            elif message.startswith("REQ_TOGGLE_SB:"):
                clave_ingresada = message[14:]
                if clave_ingresada == CLAVE_ADMIN:
                    soundboard_bloqueado = not soundboard_bloqueado
                    estado_msg = "SB_STATE:LOCKED" if soundboard_bloqueado else "SB_STATE:UNLOCKED"
                    # Le avisamos a TODOS los conectados para que bloqueen/desbloqueen sus botones
                    for c in CLIENTES:
                        if c.open:
                            await c.send(estado_msg)
                else:
                    # Si le pifió a la clave, solo le avisamos al que la mandó
                    await websocket.send("ADMIN_FAIL")

            # 3. CUALQUIER OTRO MENSAJE (Dibujos, Texto, Fotos, Sonidos)
            else:
                # Se retransmite a TODOS los demás usuarios conectados
                for c in CLIENTES:
                    if c != websocket and c.open:
                        await c.send(message)

    except websockets.exceptions.ConnectionClosedError:
        pass
    finally:
        if websocket in CLIENTES:
            CLIENTES.remove(websocket)

async def main():
    # Render asigna dinámicamente un puerto en la variable de entorno PORT
    port = int(os.environ.get("PORT", 8080))
    async with websockets.serve(handler, "0.0.0.0", port):
        print(f"Servidor corriendo en el puerto {port}")
        await asyncio.Future()  # Mantiene el servidor corriendo indefinidamente

if __name__ == "__main__":
    asyncio.run(main())