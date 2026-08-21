import asyncio
import datetime
import os

import websockets
from websockets.exceptions import ConnectionClosed


VERSION_MINIMA = "1.0.0"

# Mejor poner esta clave como variable de entorno en Render.
CLAVE_ADMIN = os.environ.get(Daviconsualiento1414)

CLIENTES = set()
soundboard_bloqueado = False


async def enviar_a_todos(mensaje):
    """
    Envía un mensaje a todos los clientes conectados.
    Si alguno ya se cerró, se elimina del conjunto.
    """
    for cliente in list(CLIENTES):
        try:
            await cliente.send(mensaje)
        except ConnectionClosed:
            CLIENTES.discard(cliente)
        except Exception as e:
            print(f"Error enviando a cliente: {e}")
            CLIENTES.discard(cliente)


async def handler(websocket):
    global soundboard_bloqueado

    CLIENTES.add(websocket)

    apodo_usuario = "Anónimo"
    autenticado = False

    try:
        async for message in websocket:

            # ==========================================================
            # HANDSHAKE INICIAL
            # ==========================================================
            if not autenticado:

                if message.startswith("INIT:"):
                    partes = message[5:].split("|", 1)

                    version_cli = partes[0]
                    apodo_usuario = (
                        partes[1]
                        if len(partes) > 1
                        else "Anónimo"
                    )

                    # Comparación correcta de versiones.
                    try:
                        version_cliente = tuple(
                            map(int, version_cli.split("."))
                        )

                        version_minima = tuple(
                            map(int, VERSION_MINIMA.split("."))
                        )

                    except ValueError:
                        await websocket.send(
                            "ERR_VER:La versión del cliente no es válida."
                        )
                        await websocket.close()
                        return

                    if version_cliente < version_minima:
                        await websocket.send(
                            f"ERR_VER:"
                            f"Tu cliente está desactualizado "
                            f"(v{version_cli}). "
                            f"La versión mínima requerida es "
                            f"v{VERSION_MINIMA}."
                        )
                        await websocket.close()
                        return

                    autenticado = True

                    hora = datetime.datetime.now().strftime("%H:%M")

                    msg_sistema = (
                        f"TEXT:{hora}|"
                        f"SISTEMA|"
                        f"#27ae60|"
                        f"{apodo_usuario} se unió al chat.|"
                        f"NONE"
                    )

                    await enviar_a_todos(msg_sistema)

                    # Enviar estado actual del soundboard al recién llegado.
                    if soundboard_bloqueado:
                        try:
                            await websocket.send(
                                "SB_STATE:LOCKED"
                            )
                        except ConnectionClosed:
                            pass

                else:
                    await websocket.send(
                        "ERR_VER:"
                        "Cliente no compatible o muy antiguo."
                    )
                    await websocket.close()
                    return

            # ==========================================================
            # CLIENTE YA AUTENTICADO
            # ==========================================================
            else:

                # ------------------------------------------------------
                # TOGGLE SOUNDBOARD
                # ------------------------------------------------------
                if message.startswith("REQ_TOGGLE_SB:"):

                    clave_ingresada = message[
                        len("REQ_TOGGLE_SB:")
                    ]

                    if clave_ingresada == CLAVE_ADMIN:

                        soundboard_bloqueado = (
                            not soundboard_bloqueado
                        )

                        estado_msg = (
                            "SB_STATE:LOCKED"
                            if soundboard_bloqueado
                            else "SB_STATE:UNLOCKED"
                        )

                        await enviar_a_todos(estado_msg)

                    else:
                        try:
                            await websocket.send("ADMIN_FAIL")
                        except ConnectionClosed:
                            pass

                # ------------------------------------------------------
                # CUALQUIER OTRO MENSAJE
                # ------------------------------------------------------
                else:

                    for cliente in list(CLIENTES):

                        # No hace falta devolverlo al emisor.
                        if cliente == websocket:
                            continue

                        try:
                            await cliente.send(message)

                        except ConnectionClosed:
                            CLIENTES.discard(cliente)

                        except Exception as e:
                            print(
                                f"Error retransmitiendo mensaje: {e}"
                            )
                            CLIENTES.discard(cliente)

    except ConnectionClosed:
        pass

    except Exception as e:
        print(f"Error en handler: {e}")

    finally:
        CLIENTES.discard(websocket)

        print(
            f"Cliente desconectado: {apodo_usuario} "
            f"| clientes activos: {len(CLIENTES)}"
        )


async def main():
    # Render establece PORT automáticamente.
    port = int(os.environ.get("PORT", "10000"))

    print(f"Iniciando servidor en 0.0.0.0:{port}")

    async with websockets.serve(
        handler,
        "0.0.0.0",
        port
    ):
        print(f"Servidor corriendo en el puerto {port}")

        # Mantener el servidor vivo.
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())
