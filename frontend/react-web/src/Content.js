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
import KnowledgeBaseResult from './KnowledgeBaseResult';
import './App.css';
import { apiKey, apiUrl, avatarFileName, avatarJawboneName, knowledgeBaseId, bedrockRegion } from './aws-exports'
import { logInfo, logError, logDebug, logWarn, KnowledgeBaseLogger, WebSocketLogger } from './utils/debugUtils';

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
            // Close any existing audio context
            if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
                await audioContextRef.current.close();
            }
            
            // Create new audio context
            audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: SAMPLE_RATE,
                latencyHint: 'interactive'
            });

            // Wait for audio context to be fully initialized
            await audioContextRef.current.resume();
            
            // Add audio worklet module with retry logic
            let retries = 0;
            const maxRetries = 3;
            
            while (retries < maxRetries) {
                try {
                    await audioContextRef.current.audioWorklet.addModule('/audio-processor.js');
                    break; // Success, exit retry loop
                } catch (error) {
                    retries++;
                    console.warn(`Failed to load audio worklet (attempt ${retries}/${maxRetries}):`, error);
                    if (retries >= maxRetries) {
                        throw error; // Max retries reached, propagate error
                    }
                    await new Promise(resolve => setTimeout(resolve, 500)); // Wait before retry
                }
            }
            
            // Create audio worklet node
            audioWorkletNodeRef.current = new AudioWorkletNode(
                audioContextRef.current,
                'audio-processor',
                {
                    outputChannelCount: [1],
                    processorOptions: {
                        sampleRate: SAMPLE_RATE
                    }
                }
            );

            // Handle messages from audio processor
            audioWorkletNodeRef.current.port.onmessage = (event) => {
                if (event.data === 'needData') {
                    setTalking(false);
                } else if (event.data === 'stopped') {
                    setTalking(false);
                } else if (event.data === 'bufferReset') {
                    console.warn('Audio buffer was reset, attempting to recover connection');
                    // Try to recover by reinitializing the connection if engaged
                    if (isEngaged) {
                        // Briefly disengage and re-engage
                        setEngaged(false);
                        setTimeout(() => {
                            setEngaged(true);
                        }, 1000);
                    }
                }
            };

            // Connect to audio output
            audioWorkletNodeRef.current.connect(audioContextRef.current.destination);
            
            console.log('AudioWorklet initialized successfully');
        } catch (error) {
            console.error('Failed to initialize AudioWorklet:', error);
            // Try to recover by setting up a basic audio context
            try {
                if (!audioContextRef.current || audioContextRef.current.state === 'closed') {
                    audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({
                        sampleRate: SAMPLE_RATE
                    });
                }
                await audioContextRef.current.resume();
            } catch (fallbackError) {
                console.error('Failed to initialize fallback audio context:', fallbackError);
            }
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
                    logInfo('WebSocket', 'Connected successfully', { url: apiUrl });
                    WebSocketLogger.logConnection(apiUrl);
                    reconnectAttempts = 0; // Reset reconnect attempts on successful connection
                    await initMicrophone();
                    
                    // Send knowledge base configuration
                    if (wsRef.current?.readyState === WebSocket.OPEN) {
                        try {
                            const configMessage = {
                                type: 'config',
                                knowledgeBaseId: knowledgeBaseId,
                                region: bedrockRegion
                            };
                            
                            logInfo('WebSocket', 'Sending knowledge base configuration', configMessage);
                            wsRef.current.send(JSON.stringify(configMessage));
                            WebSocketLogger.logMessage('sent', configMessage);
                        } catch (error) {
                            logError('WebSocket', 'Error sending knowledge base configuration', error);
                        }
                    }
                    
                    // Setup heartbeat to keep connection alive
                    heartbeatInterval = setInterval(() => {
                        if (wsRef.current?.readyState === WebSocket.OPEN) {
                            try {
                                // Send a ping message to keep the connection alive
                                wsRef.current.send(JSON.stringify({ type: 'ping' }));
                            } catch (error) {
                                logError('WebSocket', 'Error sending heartbeat', error);
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
                                    // Add a small delay to ensure the audio worklet is ready
                                    setTimeout(() => {
                                        try {
                                            audioWorkletNodeRef.current?.port.postMessage({
                                                type: 'data',
                                                audio: float32Array
                                            });
                                            
                                            if (!isTalking) {
                                                setTalking(true);
                                            }
                                        } catch (error) {
                                            console.error('Error sending audio data to worklet:', error);
                                            // Try to recover from audio processing errors
                                            audioWorkletNodeRef.current?.port.postMessage({
                                                type: 'clear'
                                            });
                                        }
                                    }, 10);
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
                        } else if (chunk.event === 'kb_processing') {
                            // Handle knowledge base processing notification
                            try {
                                logInfo('KnowledgeBase', 'Processing event received', chunk.data);
                                
                                let processingData;
                                try {
                                    processingData = JSON.parse(chunk.data);
                                    logDebug('KnowledgeBase', 'Processing details', processingData);
                                } catch (parseError) {
                                    logError('KnowledgeBase', 'Failed to parse processing data', {
                                        error: parseError,
                                        rawData: chunk.data
                                    });
                                    processingData = { message: "Processing document query..." };
                                }
                                
                                // Log knowledge base ID if available
                                if (processingData.knowledgeBaseId) {
                                    logInfo('KnowledgeBase', 'Using knowledge base ID', processingData.knowledgeBaseId);
                                    
                                    // Verify it matches our configured ID
                                    if (processingData.knowledgeBaseId !== knowledgeBaseId) {
                                        logWarn('KnowledgeBase', 'Knowledge base ID mismatch', {
                                            expected: knowledgeBaseId,
                                            actual: processingData.knowledgeBaseId
                                        });
                                    }
                                } else {
                                    logWarn('KnowledgeBase', 'No knowledge base ID specified in processing data');
                                }
                                
                                // Enable knowledge base mode in audio processor
                                audioWorkletNodeRef.current?.port.postMessage({
                                    type: 'kb_mode_on'
                                });
                                
                                // Show loading indicator for knowledge base queries
                                setMessages(messages => [...messages, {
                                    isMine: false,
                                    isProcessing: true,
                                    text: processingData.message || "Processing document query..."
                                }]);
                            } catch (error) {
                                logError('KnowledgeBase', 'Error processing notification', {
                                    error,
                                    rawData: chunk.data
                                });
                                
                                // Show error message
                                setMessages(messages => [...messages, {
                                    isMine: false,
                                    text: `Error processing knowledge base query: ${error.message}`
                                }]);
                            }
                        } else if (chunk.event === 'knowledge_base') {
                            // Handle knowledge base responses
                            try {
                                logInfo('KnowledgeBase', 'Response received');
                                logDebug('KnowledgeBase', 'Raw response data', chunk.data);
                                
                                let kbData;
                                try {
                                    kbData = JSON.parse(chunk.data);
                                    KnowledgeBaseLogger.logResponse(kbData);
                                } catch (parseError) {
                                    logError('KnowledgeBase', 'Failed to parse response data', {
                                        error: parseError,
                                        rawData: chunk.data
                                    });
                                    throw new Error(`Failed to parse knowledge base response: ${parseError.message}`);
                                }
                                
                                // Validate knowledge base data structure
                                if (!kbData) {
                                    logError('KnowledgeBase', 'Empty response received');
                                    throw new Error('Empty knowledge base response received');
                                }
                                
                                // Log detailed information about the knowledge base response
                                logDebug('KnowledgeBase', 'Response structure', {
                                    hasTitle: !!kbData.title,
                                    hasContent: !!kbData.content,
                                    contentType: kbData.content ? (Array.isArray(kbData.content) ? 'array' : typeof kbData.content) : 'undefined',
                                    contentLength: kbData.content ? (Array.isArray(kbData.content) ? kbData.content.length : kbData.content.length) : 0,
                                    hasSource: !!kbData.source,
                                    hasMetadata: !!kbData.metadata
                                });
                                
                                // Check if the response contains retrievalResults directly
                                if (kbData.retrievalResults && Array.isArray(kbData.retrievalResults)) {
                                    logInfo('KnowledgeBase', 'Direct Bedrock response detected, transforming to expected format');
                                    
                                    // Transform the Bedrock response to the expected format
                                    const transformedContent = kbData.retrievalResults.map(item => ({
                                        content: item.content?.text || 'No content available',
                                        source: item.location?.s3Location?.uri || 'Unknown source',
                                        score: item.score || 0
                                    }));
                                    
                                    // Replace the original content with the transformed content
                                    kbData = {
                                        title: "Knowledge Base Results",
                                        content: transformedContent,
                                        metadata: {
                                            processing_time: {
                                                retrieval: "N/A",
                                                generation: "N/A",
                                                total: "N/A"
                                            }
                                        }
                                    };
                                    
                                    logDebug('KnowledgeBase', 'Transformed response', kbData);
                                }
                                
                                // Disable knowledge base mode in audio processor
                                audioWorkletNodeRef.current?.port.postMessage({
                                    type: 'kb_mode_off'
                                });
                                
                                // Small delay to ensure audio processing continues
                                setTimeout(() => {
                                    setMessages(messages => {
                                        // Remove the processing message
                                        const filteredMessages = messages.filter(m => !m.isProcessing);
                                        
                                        // Add the actual knowledge base result
                                        return [...filteredMessages, {
                                            isMine: false,
                                            isKnowledgeBase: true,
                                            title: kbData.title || "Knowledge Base Result",
                                            content: kbData.content || "No content available",
                                            source: kbData.source,
                                            metadata: kbData.metadata
                                        }];
                                    });
                                }, 500);
                            } catch (error) {
                                logError('KnowledgeBase', 'Error processing response', {
                                    error,
                                    rawData: chunk.data
                                });
                                
                                // Add fallback message on error with specific error details
                                setMessages(messages => {
                                    // Remove the processing message
                                    const filteredMessages = messages.filter(m => !m.isProcessing);
                                    
                                    // Add error message with specific error details
                                    return [...filteredMessages, {
                                        isMine: false,
                                        text: `Error retrieving information from the knowledge base: ${error.message}. Please try rephrasing your question.`
                                    }];
                                });
                                
                                // Disable knowledge base mode in audio processor even on error
                                audioWorkletNodeRef.current?.port.postMessage({
                                    type: 'kb_mode_off'
                                });
                            }
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
                    logError('WebSocket', 'Connection error', {
                        error,
                        readyState: wsRef.current?.readyState,
                        url: apiUrl
                    });
                    WebSocketLogger.logError(error);
                    
                    // Add error message to chat
                    setMessages(messages => [...messages, {
                        isMine: false,
                        text: "Connection error. Please try reconnecting."
                    }]);
                    
                    setTalking(false);
                };
                
                wsRef.current.onclose = (event) => {
                    logInfo('WebSocket', 'Connection closed', {
                        code: event.code,
                        reason: event.reason,
                        wasClean: event.wasClean
                    });
                    WebSocketLogger.logClose(event);
                    
                    setTalking(false);
                    
                    // Clear heartbeat interval
                    if (heartbeatInterval) {
                        clearInterval(heartbeatInterval);
                        heartbeatInterval = null;
                    }
                    
                    // Attempt to reconnect if still engaged
                    if (isEngaged && reconnectAttempts < maxReconnectAttempts) {
                        logInfo('WebSocket', 'Attempting to reconnect', {
                            attempt: reconnectAttempts + 1,
                            maxAttempts: maxReconnectAttempts
                        });
                        
                        reconnectAttempts++;
                        
                        reconnectTimeout = setTimeout(() => {
                            connect();
                        }, reconnectInterval);
                    } else if (reconnectAttempts >= maxReconnectAttempts) {
                        logError('WebSocket', 'Max reconnection attempts reached');
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
                
                {/* Chat messages display */}
                <div className="chat-messages">
                    {messages.map((message, index) => (
                        <div key={index} className={`message ${message.isMine ? 'mine' : 'assistant'}`}>
                            {message.isProcessing ? (
                                <div className="message-text processing">
                                    {message.text} <Spinner animation="border" size="sm" />
                                </div>
                            ) : message.isKnowledgeBase ? (
                                <KnowledgeBaseResult
                                    title={message.title}
                                    content={message.content}
                                    source={message.source}
                                    metadata={message.metadata}
                                />
                            ) : (
                                <div className="message-text">{message.text}</div>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

export default Content;
