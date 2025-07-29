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
Base64 Audio Serializer for WebSocket Communication

This module provides a serializer for handling base64-encoded audio data over WebSocket connections.
It supports bidirectional conversion between raw PCM audio data and base64-encoded format, with
optional resampling capabilities.

The serializer is designed to work with the Pipecat audio processing pipeline and handles:
- Serialization of outgoing audio frames to base64
- Deserialization of incoming base64 data to audio frames
- Audio resampling when input/output sample rates differ
- Special handling for interruption events
"""

from typing import Optional
from pydantic import BaseModel
import base64
import json
from loguru import logger

from pipecat.frames.frames import (
    AudioRawFrame,
    Frame,
    InputAudioRawFrame,
    StartInterruptionFrame,
    StartFrame,
)
from pipecat.serializers.base_serializer import FrameSerializer, FrameSerializerType
from pipecat.audio.utils import create_stream_resampler

class Base64AudioSerializer(FrameSerializer):
    """Serializer for base64-encoded audio data over WebSocket.
    
    Handles conversion between raw PCM audio data and base64-encoded format,
    with optional resampling support.
    """

    class InputParams(BaseModel):
        """Configuration parameters for Base64AudioSerializer.

        Parameters:
            target_sample_rate: Target sample rate for audio processing
            sample_rate: Optional override for pipeline input sample rate
        """
        target_sample_rate: int = 16000
        sample_rate: Optional[int] = None

    def __init__(
        self,
        params: Optional[InputParams] = None,
    ):
        """Initialize the Base64AudioSerializer.

        Args:
            params: Configuration parameters for sample rates and resampling
        """
        self._params = params or Base64AudioSerializer.InputParams()
        self._target_sample_rate = self._params.target_sample_rate
        self._sample_rate = 0  # Pipeline input rate

        # Initialize resamplers for input and output
        self._input_resampler = create_stream_resampler()
        self._output_resampler = create_stream_resampler()

    @property
    def type(self) -> FrameSerializerType:
        """Gets the serializer type.

        Returns:
            The serializer type (TEXT for base64-encoded data)
        """
        return FrameSerializerType.TEXT

    async def setup(self, frame: StartFrame):
        """Sets up the serializer with pipeline configuration.

        Args:
            frame: The StartFrame containing pipeline configuration including sample rates
        """
        self._sample_rate = self._params.sample_rate or frame.audio_in_sample_rate

    async def serialize(self, frame: Frame) -> str | bytes | None:
        """Serializes a Pipecat frame to base64-encoded format.

        Args:
            frame: The Pipecat frame to serialize (AudioRawFrame or StartInterruptionFrame)

        Returns:
            JSON string containing base64-encoded audio data or control events,
            or None if frame type is not handled

        The serialized format is a JSON object with:
        - For audio: {"event": "media", "data": "<base64-encoded-audio>"}
        - For interruption: {"event": "stop"}
        """
        try:
            if isinstance(frame, StartInterruptionFrame):
                response = {"event": "stop"}
                return json.dumps(response)

            elif isinstance(frame, AudioRawFrame):
                # Resample if needed
                if frame.sample_rate != self._target_sample_rate:
                    resampled_data = await self._output_resampler.resample(
                        frame.audio,
                        frame.sample_rate,
                        self._target_sample_rate
                    )
                else:
                    resampled_data = frame.audio

                # Encode to base64
                encoded_data = base64.b64encode(resampled_data).decode('utf-8')

                response = {"event": "media", "data": encoded_data}
                return json.dumps(response)

            else:
                print('Unhandled frame: ', frame)
                return None

        except Exception as e:
            logger.error(f"Error serializing audio frame: {e}")
            return None

    async def deserialize(self, data: str | bytes) -> Frame | None:
        """Deserializes base64-encoded data to Pipecat frames.

        Args:
            data: The base64-encoded audio data as string or bytes

        Returns:
            An InputAudioRawFrame containing the decoded and resampled audio data,
            or None if deserialization fails

        Process:
        1. Decode base64 data to bytes
        2. Convert to numpy array (16-bit PCM format)
        3. Resample if needed
        4. Create InputAudioRawFrame with processed audio
        """
        try:
            # Check if this is a JSON message
            if isinstance(data, str) and data.startswith('{'):
                try:
                    # Try to parse as JSON
                    json_data = json.loads(data)
                    
                    # Handle configuration message
                    if json_data.get('type') == 'config':
                        print(f"Received configuration message: {json_data}")
                        
                        # Extract region
                        region = json_data.get('region')
                        
                        # Extract Bedrock agent configuration
                        agent_id = json_data.get('bedrockAgentId')
                        agent_alias_id = json_data.get('bedrockAgentAliasId')
                        
                        # Initialize Bedrock agent client if region is provided
                        if region:
                            # Initialize Bedrock agent client if agent ID is provided
                            if agent_id and agent_alias_id:
                                from bedrock_agent_functions import initialize_bedrock_agent_client
                                initialize_bedrock_agent_client(region)
                                print(f"Initialized Bedrock agent client in region {region}")
                                
                                # Set the agent configuration in the LLM service
                                # This will be handled by the pipeline later
                                pass
                        
                        return None
                    
                    # Handle ping message
                    if json_data.get('type') == 'ping':
                        print("Received ping message")
                        return None
                    
                    # Other JSON messages are not handled
                    print(f"Unhandled JSON message: {json_data}")
                    return None
                    
                except json.JSONDecodeError:
                    # Not valid JSON, continue with base64 decoding
                    pass
            
            # Decode base64 data
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            
            decoded_data = base64.b64decode(data)
            
            # Convert to numpy array (assuming 16-bit PCM)
            import numpy as np
            audio_data = np.frombuffer(decoded_data, dtype=np.int16)

            # Resample if needed
            if self._target_sample_rate != self._sample_rate:
                audio_data = await self._input_resampler.resample(
                    audio_data,
                    self._target_sample_rate,
                    self._sample_rate
                )

            # Convert back to bytes
            decoded_data = audio_data.tobytes()

            return InputAudioRawFrame(
                audio=decoded_data,
                num_channels=1,
                sample_rate=self._sample_rate
            )

        except Exception as e:
            logger.error(f"Error deserializing audio data: {e}")
            return None
