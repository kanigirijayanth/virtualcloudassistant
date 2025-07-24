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
 * Main Content Component
 * 
 * This component handles the core functionality of the Virtual Cloud Assistant,
 * including audio streaming, WebSocket communication, and avatar control.
 */

import React, { useState, useRef, useEffect } from 'react';
import { getCurrentUser, signOut } from 'aws-amplify/auth';
import { Authenticator } from '@aws-amplify/ui-react';
import { Navbar, Spinner, Modal, Button, Nav, NavDropdown } from 'react-bootstrap';

import Avatar from './Avatar'
import './App.css';
import { apiKey, apiUrl, avatarFileName, avatarJawboneName } from './aws-exports'

// Audio sample rate. It should match the same in the backend to avoid resampling overhead.
const SAMPLE_RATE = 16000;

/**
 * Content Component
 * Manages the authenticated user interface and audio communication
 * 
 * @param {Object} props Component properties
 * @param {Function} props.signOut Function to handle user sign out
 * @param {Object} props.user Current authenticated user
 */
function Content({ signOut, user }) {
    // State management
    const [messages, setMessages] = useState([]);
    const [isTalking, setTalking] = useState(false);
    const [headerVisible, setHeaderVisible] = useState(true);
    const [isEngaged, setEngaged] = useState(false);

    // Audio context and processing references
    const audioContextRef = useRef(null);
    const audioWorkletNodeRef = useRef(null);
    const wsRef = useRef(null);

    /**
     * Converts Float32Array audio data to 16-bit PCM format.
     * 
     * @param {Float32Array} input Audio data in float format
     * @returns {Int16Array} Audio data in 16-bit PCM format
     */
    const floatToPcm16 = (input) => {
        const output = new Int16Array(input.length);
        for (let i = 0; i < input.length; i++) {
            const s = Math.max(-1, Math.min(1, input[i]));
            output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return output;
    };

    /**
     * Converts 16-bit PCM audio data to Float32Array format.
     * 
     * @param {ArrayBuffer} buffer Audio data in PCM format
     * @returns {Float32Array} Audio data in float format
     */
    const pcm16ToFloat = (buffer) => {
        const dataView = new DataView(buffer);
        const float32 = new Float32Array(buffer.byteLength / 2);
        for (let i = 0; i < float32.length; i++) {
            const int16 = dataView.getInt16(i * 2, true);
            float32[i] = int16 / 32768.0;
        }
        return float32;
    };

    /**
     * Initializes audio context and AudioWorklet for audio processing
     */
    const initAudioWorklet = async () => {
        try {
            audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: SAMPLE_RATE
            });

            await audioContextRef.current.audioWorklet.addModule('/audio-processor.js');
            audioWorkletNodeRef.current = new AudioWorkletNode(
                audioContextRef.current,
                'audio-processor'
            );

            // Handle messages from audio processor
            audioWorkletNodeRef.current.port.onmessage = (event) => {
                if (event.data === 'needData') {
                    setTalking(false);
                }
            };

            audioWorkletNodeRef.current.connect(audioContextRef.current.destination);
            await audioContextRef.current.resume();

            console.log('AudioWorklet initialized successfully');
        } catch (error) {
            console.error('Failed to initialize AudioWorklet:', error);
        }
    };

    /**
     * Initializes microphone input for audio capture
     */
    const initMicrophone = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const source = audioContextRef.current.createMediaStreamSource(stream);
            const processor = audioContextRef.current.createScriptProcessor(4096, 1, 1);

            source.connect(processor);

            // Connect to destination with zero gain to prevent feedback
            const gainNode = audioContextRef.current.createGain();
            gainNode.gain.value = 0;
            processor.connect(gainNode);
            gainNode.connect(audioContextRef.current.destination);

            // Process and send audio data
            processor.onaudioprocess = (event) => {
                const input = event.inputBuffer.getChannelData(0);
                const pcm16 = floatToPcm16(input);
                const buffer = new ArrayBuffer(pcm16.length * 2);
                const view = new DataView(buffer);
                pcm16.forEach((value, index) => view.setInt16(index * 2, value, true));
                const bytes = new Uint8Array(buffer);
                const base64 = btoa(String.fromCharCode.apply(null, bytes));

                if (wsRef.current?.readyState === WebSocket.OPEN) {
                    wsRef.current.send(base64);
                }
            };
        } catch (error) {
            console.error('Failed to initialize microphone:', error);
        }
    };

    // Setup and cleanup effect
    useEffect(() => {
        let heartbeatInterval;
        let reconnectTimeout;
        
        const cleanup = () => {
            // Clear any pending intervals/timeouts
            if (heartbeatInterval) clearInterval(heartbeatInterval);
            if (reconnectTimeout) clearTimeout(reconnectTimeout);
            
            // Close WebSocket connection
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.close();
            }
            
            // Clean up audio context
            if (audioContextRef.current?.state !== 'closed') {
                if (audioWorkletNodeRef.current) {
                    audioWorkletNodeRef.current.disconnect();
                }
                if (audioContextRef.current) {
                    audioContextRef.current.close();
                }
            }
        };

        if (!isEngaged) {
            cleanup();
            return;
        }

        // Initialize audio and WebSocket with reconnection support
        const initAudio = async () => {
            await initAudioWorklet();
            setupWebSocketConnection();
        };
        
        // Setup WebSocket connection with reconnection logic
        const setupWebSocketConnection = () => {
            let reconnectAttempts = 0;
            const maxReconnectAttempts = 5;
            const reconnectInterval = 2000; // 2 seconds
            
            const connect = () => {
                wsRef.current = new WebSocket(apiUrl, apiKey);
                
                wsRef.current.onopen = async () => {
                    console.log('WebSocket connected');
                    reconnectAttempts = 0; // Reset reconnect attempts on successful connection
                    await initMicrophone();
                    
                    // Setup heartbeat to keep connection alive
                    heartbeatInterval = setInterval(() => {
                        if (wsRef.current?.readyState === WebSocket.OPEN) {
                            try {
                                // Send a ping message to keep the connection alive
                                wsRef.current.send(JSON.stringify({ type: 'ping' }));
                            } catch (error) {
                                console.error('Error sending heartbeat:', error);
                            }
                        }
                    }, 30000); // Every 30 seconds
                };
                
                wsRef.current.onmessage = async (event) => {
                    try {
                        const chunk = JSON.parse(event.data);
                        
                        if (chunk.event === 'stop') {
                            console.log('Interruption');
                            audioWorkletNodeRef.current?.port.postMessage({
                                type: 'stop'
                            });
                            
                            setTalking(false);
                            
                        } else if (chunk.event === 'media') {
                            try {
                                const base64Data = chunk.data;
                                const binaryString = atob(base64Data);
                                const bytes = new Uint8Array(binaryString.length);
                                for (let i = 0; i < binaryString.length; i++) {
                                    bytes[i] = binaryString.charCodeAt(i);
                                }
                                
                                const float32Array = pcm16ToFloat(bytes.buffer);
                                
                                if (float32Array.length > 0) {
                                    audioWorkletNodeRef.current?.port.postMessage({
                                        type: 'data',
                                        audio: float32Array
                                    });
                                    
                                    if (!isTalking) {
                                        setTalking(true);
                                    }
                                }
                            } catch (error) {
                                console.error('Error processing audio data:', error);
                                // Try to recover from audio processing errors
                                audioWorkletNodeRef.current?.port.postMessage({
                                    type: 'clear'
                                });
                            }
                        } else if (chunk.event === 'text') {
                            setMessages(messages => [...messages, {
                                isMine: chunk.speaker === 'user',
                                text: chunk.data
                            }]);
                        } else if (chunk.type === 'pong') {
                            // Handle heartbeat response if needed
                            console.debug('Received heartbeat response');
                        }
                    } catch (error) {
                        console.error('Error processing WebSocket message:', error);
                        // Try to recover from the error
                        if (audioWorkletNodeRef.current) {
                            audioWorkletNodeRef.current.port.postMessage({
                                type: 'clear'
                            });
                        }
                    }
                };
                
                wsRef.current.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    setTalking(false);
                };
                
                wsRef.current.onclose = (event) => {
                    console.log('WebSocket closed', event);
                    setTalking(false);
                    
                    // Clear heartbeat interval
                    if (heartbeatInterval) {
                        clearInterval(heartbeatInterval);
                        heartbeatInterval = null;
                    }
                    
                    // Attempt to reconnect if still engaged
                    if (isEngaged && reconnectAttempts < maxReconnectAttempts) {
                        console.log(`Attempting to reconnect (${reconnectAttempts + 1}/${maxReconnectAttempts})...`);
                        reconnectAttempts++;
                        
                        reconnectTimeout = setTimeout(() => {
                            connect();
                        }, reconnectInterval);
                    } else if (reconnectAttempts >= maxReconnectAttempts) {
                        console.error('Max reconnection attempts reached');
                        setEngaged(false);
                    }
                };
            };
            
            connect();
        };

        initAudio();
        return cleanup;
    }, [isEngaged]);

    return (
        <div className="app">
            {/* Header with navigation */}
            <Navbar
                className='header'
                bg='light'
                expand='lg'
                style={{
                    transition: 'opacity 0.3s ease',
                    opacity: headerVisible ? 1 : 0,
                    pointerEvents: headerVisible ? 'auto' : 'none'
                }}
            >
                <Navbar.Brand className='px-2'>Virtual Cloud Assistant</Navbar.Brand>
                {user &&
                    <Nav className='d-flex flex-row p-2 nav-strip flex-grow-1 justify-content-end'>
                        <Nav.Link onClick={() => setHeaderVisible(false)}>
                            Immersive
                        </Nav.Link>
                        <Nav.Link onClick={() => {
                            setEngaged(!isEngaged)
                            if (isEngaged) {
                                setTalking(false)
                            }
                        }}>
                            {isEngaged ? 'Disengage' : 'Engage'}
                        </Nav.Link>
                        <Nav.Link onClick={signOut}>
                            Logout
                        </Nav.Link>
                    </Nav>
                }
            </Navbar>

            {/* Main content area with avatar */}
            <div className="container" onClick={() => setHeaderVisible(true)}>
                <Avatar
                    glbUrl={"/" + avatarFileName}
                    jawBoneName={avatarJawboneName}
                    isTalking={isTalking}
                />
            </div>
        </div>
    );
}

export default Content;
