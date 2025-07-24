/*********************************************************************************************************************
*  Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           *
*                                                                                                                    *
*  Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance        *
*  with the License. A copy of the License is located at                                                             *
*                                                                                                                    *
*      http://aws.amazon.com/asl/                                                                                    *
*                                                                                                                    *
*  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES *
*  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    *
*  and limitations under the License.                                                                                *
**********************************************************************************************************************/

/**
 * Audio Processor Worklet
 * 
 * This AudioWorklet handles real-time audio processing for the Virtual Cloud Assistant.
 * It manages a buffer of audio data and streams it to the audio output in a controlled manner.
 * 
 * Features:
 * - Buffered audio playback to prevent gaps
 * - Dynamic buffer management to prevent memory leaks
 * - Automatic request for more data when buffer runs low
 * - Improved buffer starvation handling
 */

class AudioProcessor extends AudioWorkletProcessor {
    /**
     * Initialize the audio processor.
     * Sets up the audio buffer and message handling from the main thread.
     */
    constructor() {
        super();
        this.buffer = new Float32Array(0);  // Audio data buffer
        this.position = 0;  // Current playback position in buffer
        this.isPlaying = true;  // Playback state flag
        this.lastDataTime = Date.now();  // Track when we last received data
        this.bufferThreshold = 4096;  // Minimum buffer size before requesting more data
        this.starvationTimeout = 10000;  // Increased timeout to 10 seconds
        this.needDataRequested = false;  // Flag to prevent multiple needData requests
        this.silenceBuffer = new Float32Array(128).fill(0);  // Pre-allocated silence buffer
        this.recoveryAttempts = 0;  // Track recovery attempts
        this.maxRecoveryAttempts = 3;  // Maximum number of recovery attempts

        // Handle messages from main thread
        this.port.onmessage = (event) => {
            if (event.data.type === 'data') {
                // Append new audio data to buffer
                const newBuffer = new Float32Array(this.buffer.length + event.data.audio.length);
                newBuffer.set(this.buffer);
                newBuffer.set(event.data.audio, this.buffer.length);
                this.buffer = newBuffer;
                this.isPlaying = true;
                this.lastDataTime = Date.now();
                this.needDataRequested = false;
                this.recoveryAttempts = 0;  // Reset recovery attempts on successful data receipt
            } else if (event.data.type === 'clear') {
                // Clear the buffer and reset position
                this.buffer = new Float32Array(0);
                this.position = 0;
                this.needDataRequested = false;
            } else if (event.data.type === 'stop') {
                // Clear the buffer and reset position on stop command
                this.buffer = new Float32Array(0);
                this.position = 0;
                this.isPlaying = false;
                this.needDataRequested = false;
                this.port.postMessage('stopped');
            }
        };
    }

    /**
     * Request more data from the main thread if needed
     */
    requestMoreDataIfNeeded() {
        // Check if buffer is running low and we haven't already requested data
        if (this.buffer.length - this.position < this.bufferThreshold && !this.needDataRequested) {
            this.port.postMessage('needData');
            this.needDataRequested = true;
        }
    }

    /**
     * Handle buffer starvation
     * @returns {boolean} True if starvation was handled, false if reset needed
     */
    handleStarvation(output) {
        const currentTime = Date.now();
        const timeSinceLastData = currentTime - this.lastDataTime;
        
        // If we've been waiting too long for data
        if (timeSinceLastData > this.starvationTimeout) {
            if (this.recoveryAttempts < this.maxRecoveryAttempts) {
                console.warn(`Audio buffer starved (${timeSinceLastData}ms), recovery attempt ${this.recoveryAttempts + 1}/${this.maxRecoveryAttempts}`);
                this.recoveryAttempts++;
                
                // Fill output with silence to prevent clicks
                output.fill(0);
                
                // Request more data again
                this.needDataRequested = false;
                this.requestMoreDataIfNeeded();
                
                return true;
            } else {
                console.error('Audio buffer starved for too long, resetting');
                this.buffer = new Float32Array(0);
                this.position = 0;
                this.needDataRequested = false;
                this.recoveryAttempts = 0;
                return false;
            }
        }
        
        return true;
    }

    /**
     * Process audio data.
     * Called by the audio system when it needs more audio data to play.
     * 
     * @param {Array} inputs - Array of input audio buffers (unused)
     * @param {Array} outputs - Array of output audio buffers to fill
     * @param {Object} parameters - Processing parameters (unused)
     * @returns {boolean} True to keep the processor running
     */
    process(inputs, outputs, parameters) {
        const output = outputs[0][0];  // Get first channel of first output

        if (!this.isPlaying) {
            // Fill output with silence when not playing
            output.fill(0);
            return true;
        }

        // Request more data if buffer is running low
        this.requestMoreDataIfNeeded();

        // Check if we have enough data in buffer
        if (this.buffer.length - this.position < output.length) {
            // Not enough data, handle potential starvation
            if (!this.handleStarvation(output)) {
                // Reset occurred
                output.fill(0);
                return true;
            }
            
            // Fill output with silence to prevent clicks
            output.fill(0);
            return true;
        }

        // Copy data from buffer to output
        for (let i = 0; i < output.length; i++) {
            output[i] = this.buffer[this.position + i];
        }

        this.position += output.length;

        // Clean up buffer if we've processed a significant amount
        // This prevents the buffer from growing indefinitely
        if (this.position > sampleRate * 5) {  // Clean up after 5 seconds of audio (increased from 2)
            this.buffer = this.buffer.slice(this.position);
            this.position = 0;
        }

        return true;  // Keep processor alive
    }
}

// Register the processor with the audio worklet system
registerProcessor('audio-processor', AudioProcessor);
