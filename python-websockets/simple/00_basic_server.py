import asyncio
import websockets

async def handler(websocket):
    async for message in websocket:
        print(message)
        reply = f"Data recieved as:  {message}!"
        await websocket.send(reply)

async def main():
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())