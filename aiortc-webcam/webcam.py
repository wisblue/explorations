import argparse
import asyncio
import json
import logging
import os
import platform
import ssl

from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, MediaRelay
from aiortc.rtcrtpsender import RTCRtpSender

ROOT = os.path.dirname(__file__)


relay = None
webcam = None


def create_local_tracks(play_from, decode):
    """
    创建本地播放的视频。
    play_from: path of the media if exists, otherwise use the local camera to 
               capture video in 640x480, and fps = 30 
    decode: boolean
    """
    global relay, webcam

    if play_from:
        player = MediaPlayer(play_from, decode=decode)
        return player.audio, player.video
    else:
        options = {"framerate": "30", "video_size": "640x480"}
        if relay is None:
            if platform.system() == "Darwin":
                webcam = MediaPlayer(
                    "default:none", format="avfoundation", options=options
                )
            elif platform.system() == "Windows":
                webcam = MediaPlayer(
                    "video=Integrated Camera", format="dshow", options=options
                )
            else:
                webcam = MediaPlayer("/dev/video0", format="v4l2", options=options)
            relay = MediaRelay()
        return None, relay.subscribe(webcam.video)


def force_codec(pc, sender, forced_codec):
    """
    获得所有设备支持的所有codec，然后 使用transceiver.setCodecPreferences 设置codec
    """
    kind = forced_codec.split("/")[0]
    codecs = RTCRtpSender.getCapabilities(kind).codecs
    transceiver = next(t for t in pc.getTransceivers() if t.sender == sender)
    transceiver.setCodecPreferences(
        [codec for codec in codecs if codec.mimeType == forced_codec]
    )


async def index(request):
    """
    返回inex.html 作为response
    """
    content = open(os.path.join(ROOT, "index.html"), "r").read()
    return web.Response(content_type="text/html", text=content)


async def javascript(request):
    """
    返回client.js 作为response
    """
    content = open(os.path.join(ROOT, "client.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)


async def offer(request):
    params = await request.json()
    # sdp == Session Description Protocol
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    # The RTCPeerConnection interface represents a WebRTC connection between 
    # the local computer and a remote peer. It provides methods to connect 
    # to a remote peer, maintain and monitor the connection, and close 
    # the connection once it's no longer needed.
    # ref: https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/RTCPeerConnection
    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("connectionstatechange")
    # Indicates the current state of the peer connection 
    # by returning one of the strings: new, connecting, 
    # connected, disconnected, failed, or closed.
    async def on_connectionstatechange():
        print("Connection state is %s" % pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    # open media source
    audio, video = create_local_tracks(
        args.play_from, decode=not args.play_without_decoding
    )

    if audio:
        # The RTCPeerConnection method addTrack() adds a new media track
        # to the set of tracks which will be transmitted to the other peer.
        # ref: https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/addTrack
        audio_sender = pc.addTrack(audio)
        if args.audio_codec:
            force_codec(pc, audio_sender, args.audio_codec)
        elif args.play_without_decoding:
            raise Exception("You must specify the audio codec using --audio-codec")

    if video:
        video_sender = pc.addTrack(video)
        if args.video_codec:
            force_codec(pc, video_sender, args.video_codec)
        elif args.play_without_decoding:
            raise Exception("You must specify the video codec using --video-codec")

    # The RTCPeerConnection method setRemoteDescription() sets the specified session description 
    # as the remote peer's current offer or answer. The description specifies the properties 
    # of the remote end of the connection, including the media format. The method takes 
    # a single parameter—the session description—and it returns a Promise which is fulfilled 
    # once the description has been changed, asynchronously.
    # This is typically called after receiving an offer or answer from another peer over 
    # the signaling server. Keep in mind that if setRemoteDescription() is called while 
    # a connection is already in place, it means renegotiation is underway 
    # (possibly to adapt to changing network conditions).
    # ref: https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/setRemoteDescription
    await pc.setRemoteDescription(offer)

    # The createAnswer() method on the RTCPeerConnection interface creates an SDP answer to 
    # an offer received from a remote peer during the offer/answer negotiation of a WebRTC connection. 
    # The answer contains information about any media already attached to the session, codecs 
    # and options supported by the browser, and any ICE candidates already gathered. 
    # The answer is delivered to the returned Promise, and should then be sent to the source 
    # of the offer to continue the negotiation process.
    answer = await pc.createAnswer()
    # The RTCPeerConnection method setLocalDescription() changes the local description associated 
    # with the connection. This description specifies the properties of the local end of the connection, 
    # including the media format. The method takes a single parameter—the session description—and it returns 
    # a Promise which is fulfilled once the description has been changed, asynchronously.
    # If setLocalDescription() is called while a connection is already in place, it means renegotiation 
    # is underway (possibly to adapt to changing network conditions). Because descriptions will be exchanged 
    # until the two peers agree on a configuration, the description submitted by calling setLocalDescription() 
    # does not immediately take effect. Instead, the current connection configuration remains in place until 
    # negotiation is complete. Only then does the agreed-upon configuration take effect.
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )

# create a set of peer connections
pcs = set()


async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebRTC webcam demo")
    parser.add_argument("--cert-file", help="SSL certificate file (for HTTPS)")
    parser.add_argument("--key-file", help="SSL key file (for HTTPS)")
    parser.add_argument("--play-from", help="Read the media from a file and sent it.")
    parser.add_argument(
        "--play-without-decoding",
        help=(
            "Read the media without decoding it (experimental). "
            "For now it only works with an MPEGTS container with only H.264 video."
        ),
        action="store_true",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host for HTTP server (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Port for HTTP server (default: 8080)"
    )
    parser.add_argument("--verbose", "-v", action="count")
    parser.add_argument(
        "--audio-codec", help="Force a specific audio codec (e.g. audio/opus)"
    )
    parser.add_argument(
        "--video-codec", help="Force a specific video codec (e.g. video/H264)"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.cert_file:
        ssl_context = ssl.SSLContext()
        ssl_context.load_cert_chain(args.cert_file, args.key_file)
    else:
        ssl_context = None

    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", index)
    app.router.add_get("/client.js", javascript)
    app.router.add_post("/offer", offer)
    web.run_app(app, host=args.host, port=args.port, ssl_context=ssl_context)
