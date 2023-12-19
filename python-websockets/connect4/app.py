#!/home/dennis/anaconda3/envs/dnb/bin/python

import asyncio

import websockets

# async def handler(websocket):
#     while True:
#         try:
#             message = await websocket.recv()
#         except websockets.ConnectionClosedOK:
#             break
#         print(message)

## does the same as above
async def handler(websocket):
    async for message in websocket:
        print(message)

async def main():
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())