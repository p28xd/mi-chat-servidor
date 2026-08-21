async def handler(websocket):
    global soundboard_bloqueado
    CLIENTES.add(websocket)
    apodo_usuario = "Anónimo"
    autenticado = False  # Bandera para saber si mandó INIT:

    try:
        async for message in websocket:
            # Si todavía no se identificó con la versión, SOLO aceptamos INIT:
            if not autenticado:
                if message.startswith("INIT:"):
                    partes = message[5:].split("|", 1)
                    version_cli = partes[0]
                    apodo_usuario = partes[1] if len(partes) > 1 else "Anónimo"

                    # Comparación de versión
                    if version_cli < VERSION_MINIMA:
                        await websocket.send(f"ERR_VER:Tu cliente está desactualizado (v{version_cli}). La versión mínima requerida es v{VERSION_MINIMA}.")
                        await websocket.close()
                        return
                    
                    autenticado = True
                    
                    import datetime
                    hora = datetime.datetime.now().strftime("%H:%M")
                    msg_sistema = f"TEXT:{hora}|SISTEMA|#27ae60|🟢 {apodo_usuario} se unió al chat.|NONE"
                    for c in CLIENTES:
                        if c.open:
                            await c.send(msg_sistema)

                    if soundboard_bloqueado:
                        await websocket.send("SB_STATE:LOCKED")
                else:
                    # Si el cliente viejo mandó cualquier otra cosa (ej: el "TEXT:SYSTEM..." viejo)
                    # lo desconectamos de una por no identificarse
                    await websocket.send("ERR_VER:Cliente no compatible o muy antiguo.")
                    await websocket.close()
                    return

            # Si YA ESTÁ AUTENTICADO, procesamos el resto de comandos normalmente
            else:
                if message.startswith("REQ_TOGGLE_SB:"):
                    clave_ingresada = message[14:]
                    if clave_ingresada == CLAVE_ADMIN:
                        soundboard_bloqueado = not soundboard_bloqueado
                        estado_msg = "SB_STATE:LOCKED" if soundboard_bloqueado else "SB_STATE:UNLOCKED"
                        for c in CLIENTES:
                            if c.open:
                                await c.send(estado_msg)
                    else:
                        await websocket.send("ADMIN_FAIL")

                else:
                    # Retransmitir al resto
                    for c in CLIENTES:
                        if c != websocket and c.open:
                            await c.send(message)

    except websockets.exceptions.ConnectionClosedError:
        pass
    finally:
        if websocket in CLIENTES:
            CLIENTES.remove(websocket)