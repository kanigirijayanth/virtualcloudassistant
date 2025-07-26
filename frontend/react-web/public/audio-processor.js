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
 * - Advanced buffer starvation handling with progressive recovery
 * - Knowledge base query mode with extended timeouts
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
        this.bufferThreshold = 8192;  // Minimum buffer size before requesting more data
        this.starvationTimeout = 30000;  // Increased timeout to 30 seconds for knowledge base queries
        this.normalStarvationTimeout = 20000;  // Normal timeout for regular queries
        this.kbStarvationTimeout = 30000;  // Extended timeout for knowledge base queries
        this.needDataRequested = false;  // Flag to prevent multiple needData requests
        this.silenceBuffer = new Float32Array(128).fill(0);  // Pre-allocated silence buffer
        this.recoveryAttempts = 0;  // Track recovery attempts
        this.maxRecoveryAttempts = 10;  // Increased maximum number of recovery attempts
        this.isKnowledgeBaseQuery = false;  // Flag for knowledge base query mode
        this.silenceFillCount = 0;  // Count of consecutive silence fills
        this.maxSilenceFills = 100;  // Maximum number of consecutive silence fills before resetting
        this.adaptiveBufferMode = false;  // Flag for adaptive buffer mode

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
                this.silenceFillCount = 0;  // Reset silence fill count
            } else if (event.data.type === 'clear') {
                // Clear the buffer and reset position
                this.buffer = new Float32Array(0);
                this.position = 0;
                this.needDataRequested = false;
                this.silenceFillCount = 0;
            } else if (event.data.type === 'stop') {
                // Clear the buffer and reset position on stop command
                this.buffer = new Float32Array(0);
                this.position = 0;
                this.isPlaying = false;
                this.needDataRequested = false;
                this.silenceFillCount = 0;
                this.port.postMessage('stopped');
            } else if (event.data.type === 'kb_mode_on') {
                // Enable knowledge base query mode with extended timeout
                this.isKnowledgeBaseQuery = true;
                this.starvationTimeout = this.kbStarvationTimeout;
                this.adaptiveBufferMode = true;
                console.log('Knowledge base query mode enabled');
            } else if (event.data.type === 'kb_mode_off') {
                // Disable knowledge base query mode
                this.isKnowledgeBaseQuery = false;
                this.starvationTimeout = this.normalStarvationTimeout;
                this.adaptiveBufferMode = false;
                console.log('Knowledge base query mode disabled');
            }
        };
    }

    /**
     * Request more data from the main thread if needed
     */
    requestMoreDataIfNeeded() {
        // Check if buffer is running low and we haven't already requested data
        const threshold = this.adaptiveBufferMode ? this.bufferThreshold * 2 : this.bufferThreshold;
        if (this.buffer.length - this.position < threshold && !this.needDataRequested) {
            this.port.postMessage('needData');
            this.needDataRequested = true;
        }
    }

    /**
     * Handle buffer starvation with progressive recovery
     * @param {Float32Array} output - The output buffer to fill with audio
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
                this.silenceFillCount++;
                
                // Request more data again with increasing urgency
                this.needDataRequested = false;
                this.requestMoreDataIfNeeded();
                
                // If we've filled with silence too many times, try to reset
                if (this.silenceFillCount > this.maxSilenceFills) {
                    console.warn(`Too many consecutive silence fills (${this.silenceFillCount}), resetting buffer`);
                    this.buffer = new Float32Array(0);
                    this.position = 0;
                    this.silenceFillCount = 0;
                    this.port.postMessage('bufferReset');
                }
                
                return true;
            } else {
                console.error('Audio buffer starved for too long, resetting');
                this.buffer = new Float32Array(0);
                this.position = 0;
                this.needDataRequested = false;
                this.recoveryAttempts = 0;
                this.silenceFillCount = 0;
                this.port.postMessage('bufferReset');
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
            this.silenceFillCount++;
            return true;
        }

        // Copy data from buffer to output
        for (let i = 0; i < output.length; i++) {
            output[i] = this.buffer[this.position + i];
        }

        this.position += output.length;
        this.silenceFillCount = 0;  // Reset silence fill count when we successfully output audio

        // Clean up buffer if we've processed a significant amount
        // This prevents the buffer from growing indefinitely
        if (this.position > sampleRate * 5) {  // Clean up after 5 seconds of audio
            this.buffer = this.buffer.slice(this.position);
            this.position = 0;
        }

        return true;  // Keep processor alive
    }
}

// Register the processor with the audio worklet system
registerProcessor('audio-processor', AudioProcessor);
