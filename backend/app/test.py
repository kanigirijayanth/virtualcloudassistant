# /*********************************************************************************************************************
# *  Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           *
# *                                                                                                                    *
# *  Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance        *
# *  with the License. A copy of the License is located at                                                             *
# *                                                                                                                    *
# *      http://aws.amazon.com/asl/                                                                                    *
# *                                                                                                                    *
# *  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES *
# *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    *
# *  and limitations under the License.                                                                                *
# **********************************************************************************************************************/

"""
Audio Client Test Module

This module provides a test client for the Virtual Banking Assistant WebSocket server.
It handles real-time audio streaming between the client and server, including:
- Microphone input capture
- Audio playback of server responses
- WebSocket communication with base64 encoding/decoding
- Buffer management for smooth audio playback

Usage:
    python test.py

The client will connect to the configured WebSocket server and begin streaming
audio from the microphone while playing back responses from the server.
"""

import asyncio
import websockets
import pyaudio
import json
import base64

SAMPLE_RATE = 16000

class AudioClient:
    """Audio client for testing the Virtual Banking Assistant WebSocket server.
    
    Handles bidirectional audio communication with the server, including
    microphone capture and audio playback.
    """

    def __init__(self, 
        websocket_url="ws://localhost:8000/ws"
    ):
        """Initialize the audio client.
        
        Args:
            websocket_url: WebSocket server URL to connect to
        """
        self.websocket_url = websocket_url
        self.audio = pyaudio.PyAudio()
        
        # Audio parameters matching the server's expectations
        self.CHUNK = 480  # 30ms at 16kHz
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = SAMPLE_RATE
        
        # Initialize microphone input stream
        self.stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )

        # Initialize audio output stream
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = SAMPLE_RATE

        self.out_stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True
        )

    def clear_buffer(self):
        """Clear the audio buffer and stop current playback.
        
        This helps manage audio playback and prevent buffer overflow
        by clearing queued audio data and resetting the output stream.
        """
        # Clear the queue
        while not self.audio_buffer.empty():
            self.audio_buffer.get()
            
        # Stop current playback
        self.is_playing = False
        
        # Flush the output stream
        self.out_stream.stop_stream()
        self.out_stream.start_stream()
        
    async def process_server_messages(self, websocket):
        """Handle messages received from the server.
        
        Args:
            websocket: The WebSocket connection to receive messages from

        Processes different types of server messages:
        - 'media': Audio data to play back
        - 'stop': Interruption signal to clear audio buffer
        """
        try:
            while True:
                message = await websocket.recv()
                message = json.loads(message)

                if message['event'] == 'media':
                    # Decode and play audio data
                    audio_data = base64.b64decode(message['data'])
                    self.out_stream.write(audio_data)

                elif message['event'] == 'stop':
                    print('Interruption')
                    clear_buffer()

        except websockets.exceptions.ConnectionClosed:
            print("Connection to server closed")
        except Exception as e:
            print(f"Error processing server message: {e}")

    async def send_audio(self, websocket):
        """Capture and send audio data to the server.
        
        Args:
            websocket: The WebSocket connection to send audio through

        Continuously reads from the microphone and sends base64-encoded
        audio data to the server.
        """
        try:
            while True:
                # Read audio chunk from microphone
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                # Encode audio data to base64
                encoded_data = base64.b64encode(data).decode('utf-8')
                await websocket.send(encoded_data)
                await asyncio.sleep(0.01)  # Small delay to prevent overwhelming the server
        except Exception as e:
            print(f"Error sending audio: {e}")

    async def run(self):
        """Main client loop.
        
        Establishes WebSocket connection and manages bidirectional
        audio communication with the server.
        """
        try:
            async with websockets.connect(self.websocket_url) as websocket:
                print("Connected to server")
                await asyncio.gather(
                    self.send_audio(websocket),
                    self.process_server_messages(websocket)
                )
        except Exception as e:
            print(f"Connection error: {e}")
        finally:
            # Clean up audio resources
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()

    def start(self):
        """Start the client.
        
        Initializes the WebSocket connection and begins audio streaming.
        Can be interrupted with Ctrl+C.
        """
        print("Starting audio client...")
        print("Press Ctrl+C to stop")
        asyncio.run(self.run())

if __name__ == "__main__":
    client = AudioClient()
    try:
        client.start()
    except KeyboardInterrupt:
        print("\nStopping audio client...")
