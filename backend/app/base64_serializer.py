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
import traceback
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
        """Serializes a Pipecat frame to base64-encoded format with improved error handling.

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
                # Validate audio data
                if not frame.audio or len(frame.audio) == 0:
                    logger.warning("Empty audio frame received, skipping")
                    return None
                
                # Additional validation for audio quality and connection stability
                if len(frame.audio) < 32:  # Minimum frame size check
                    logger.warning("Audio frame too small, skipping")
                    return None
                
                # Check for audio corruption (all zeros or extreme values)
                import numpy as np
                try:
                    audio_array = np.frombuffer(frame.audio, dtype=np.int16)
                    if np.all(audio_array == 0):
                        logger.warning("Audio frame contains only silence, skipping")
                        return None
                    
                    # Check for clipping or extreme values that might cause crackling
                    max_val = np.max(np.abs(audio_array))
                    if max_val > 30000:  # Close to 16-bit limit
                        logger.warning(f"Audio frame has high amplitude ({max_val}), may cause crackling")
                        # Normalize to prevent crackling
                        audio_array = (audio_array * 0.8).astype(np.int16)
                        frame.audio = audio_array.tobytes()
                        
                except Exception as audio_check_error:
                    logger.warning(f"Audio validation failed: {audio_check_error}, proceeding anyway")
                
                # Resample if needed with improved error handling
                if frame.sample_rate != self._target_sample_rate:
                    try:
                        resampled_data = await self._output_resampler.resample(
                            frame.audio,
                            frame.sample_rate,
                            self._target_sample_rate
                        )
                        
                        # Validate resampled data quality
                        if not resampled_data or len(resampled_data) < 32:
                            logger.warning("Resampled audio data too small, using original")
                            resampled_data = frame.audio
                            
                    except Exception as e:
                        logger.error(f"Audio resampling failed: {e}, using original audio")
                        resampled_data = frame.audio
                else:
                    resampled_data = frame.audio

                # Final validation of resampled data
                if not resampled_data or len(resampled_data) == 0:
                    logger.warning("Empty resampled audio data, skipping")
                    return None

                # Encode to base64 with error handling
                try:
                    encoded_data = base64.b64encode(resampled_data).decode('utf-8')
                    
                    # Validate encoded data
                    if not encoded_data:
                        logger.warning("Base64 encoding resulted in empty data")
                        return None
                    
                    # Check encoded data size to prevent WebSocket message size issues
                    if len(encoded_data) > 1000000:  # 1MB limit
                        logger.warning(f"Encoded audio data too large ({len(encoded_data)} bytes), skipping")
                        return None
                        
                except Exception as e:
                    logger.error(f"Base64 encoding failed: {e}")
                    return None

                response = {"event": "media", "data": encoded_data}
                return json.dumps(response)

            else:
                print('Unhandled frame: ', frame)
                return None

        except Exception as e:
            logger.error(f"Error serializing audio frame: {e}")
            traceback.print_exc()
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
            
            # Validate base64 data
            if not data or len(data.strip()) == 0:
                logger.warning("Empty audio data received")
                return None
            
            try:
                decoded_data = base64.b64decode(data)
            except Exception as e:
                logger.error(f"Base64 decode failed: {e}")
                return None
            
            # Validate decoded data length
            if len(decoded_data) == 0:
                logger.warning("Decoded audio data is empty")
                return None
            
            # Convert to numpy array (assuming 16-bit PCM)
            import numpy as np
            try:
                audio_data = np.frombuffer(decoded_data, dtype=np.int16)
            except Exception as e:
                logger.error(f"Failed to convert audio data to numpy array: {e}")
                return None

            # Validate audio data
            if len(audio_data) == 0:
                logger.warning("Audio data array is empty")
                return None

            # Resample if needed
            if self._target_sample_rate != self._sample_rate:
                try:
                    audio_data = await self._input_resampler.resample(
                        audio_data,
                        self._target_sample_rate,
                        self._sample_rate
                    )
                except Exception as e:
                    logger.error(f"Input audio resampling failed: {e}")
                    return None

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
