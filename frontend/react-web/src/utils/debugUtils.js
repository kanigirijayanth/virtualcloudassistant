/**
 * Debug Utilities
 * 
 * This module provides utility functions for debugging and troubleshooting
 * knowledge base integration and other features.
 */

/**
 * Log levels for controlling debug output
 */
export const LogLevel = {
    ERROR: 0,
    WARN: 1,
    INFO: 2,
    DEBUG: 3,
    TRACE: 4
};

// Current log level - can be changed at runtime
let currentLogLevel = LogLevel.INFO;

/**
 * Set the current log level
 * @param {number} level - The log level to set
 */
export const setLogLevel = (level) => {
    currentLogLevel = level;
    console.log(`Log level set to: ${getLogLevelName(level)}`);
};

/**
 * Get the name of a log level
 * @param {number} level - The log level
 * @returns {string} The name of the log level
 */
export const getLogLevelName = (level) => {
    switch (level) {
        case LogLevel.ERROR: return 'ERROR';
        case LogLevel.WARN: return 'WARN';
        case LogLevel.INFO: return 'INFO';
        case LogLevel.DEBUG: return 'DEBUG';
        case LogLevel.TRACE: return 'TRACE';
        default: return 'UNKNOWN';
    }
};

/**
 * Log a message at the specified level
 * @param {number} level - The log level
 * @param {string} component - The component name
 * @param {string} message - The message to log
 * @param {any} data - Optional data to log
 */
export const log = (level, component, message, data) => {
    if (level <= currentLogLevel) {
        const timestamp = new Date().toISOString();
        const prefix = `[${timestamp}] [${getLogLevelName(level)}] [${component}]`;
        
        if (data !== undefined) {
            if (level === LogLevel.ERROR) {
                console.error(prefix, message, data);
            } else if (level === LogLevel.WARN) {
                console.warn(prefix, message, data);
            } else {
                console.log(prefix, message, data);
            }
        } else {
            if (level === LogLevel.ERROR) {
                console.error(prefix, message);
            } else if (level === LogLevel.WARN) {
                console.warn(prefix, message);
            } else {
                console.log(prefix, message);
            }
        }
    }
};

/**
 * Log an error message
 * @param {string} component - The component name
 * @param {string} message - The message to log
 * @param {any} data - Optional data to log
 */
export const logError = (component, message, data) => {
    log(LogLevel.ERROR, component, message, data);
};

/**
 * Log a warning message
 * @param {string} component - The component name
 * @param {string} message - The message to log
 * @param {any} data - Optional data to log
 */
export const logWarn = (component, message, data) => {
    log(LogLevel.WARN, component, message, data);
};

/**
 * Log an info message
 * @param {string} component - The component name
 * @param {string} message - The message to log
 * @param {any} data - Optional data to log
 */
export const logInfo = (component, message, data) => {
    log(LogLevel.INFO, component, message, data);
};

/**
 * Log a debug message
 * @param {string} component - The component name
 * @param {string} message - The message to log
 * @param {any} data - Optional data to log
 */
export const logDebug = (component, message, data) => {
    log(LogLevel.DEBUG, component, message, data);
};

/**
 * Log a trace message
 * @param {string} component - The component name
 * @param {string} message - The message to log
 * @param {any} data - Optional data to log
 */
export const logTrace = (component, message, data) => {
    log(LogLevel.TRACE, component, message, data);
};

/**
 * Knowledge Base specific logging utilities
 */
export const KnowledgeBaseLogger = {
    /**
     * Log a knowledge base query
     * @param {string} query - The query text
     * @param {string} knowledgeBaseId - The knowledge base ID
     */
    logQuery: (query, knowledgeBaseId) => {
        logInfo('KnowledgeBase', `Query: "${query}"`, { knowledgeBaseId });
    },
    
    /**
     * Log a knowledge base response
     * @param {object} response - The response object
     */
    logResponse: (response) => {
        logDebug('KnowledgeBase', 'Response received', response);
    },
    
    /**
     * Log a knowledge base error
     * @param {Error} error - The error object
     * @param {string} context - Additional context
     */
    logError: (error, context) => {
        logError('KnowledgeBase', `Error: ${context}`, error);
    }
};

/**
 * WebSocket specific logging utilities
 */
export const WebSocketLogger = {
    /**
     * Log a WebSocket connection
     * @param {string} url - The WebSocket URL
     */
    logConnection: (url) => {
        logInfo('WebSocket', `Connected to ${url}`);
    },
    
    /**
     * Log a WebSocket message
     * @param {string} direction - 'sent' or 'received'
     * @param {object} message - The message object
     */
    logMessage: (direction, message) => {
        logDebug('WebSocket', `Message ${direction}`, message);
    },
    
    /**
     * Log a WebSocket error
     * @param {Error} error - The error object
     */
    logError: (error) => {
        logError('WebSocket', 'Error', error);
    },
    
    /**
     * Log a WebSocket close event
     * @param {Event} event - The close event
     */
    logClose: (event) => {
        logInfo('WebSocket', `Connection closed: ${event.code} ${event.reason}`);
    }
};

// Enable debug mode in the console
window.enableDebug = () => {
    setLogLevel(LogLevel.DEBUG);
    return 'Debug mode enabled. Use window.setLogLevel(level) to change log level.';
};

// Set log level from the console
window.setLogLevel = setLogLevel;

// Export log levels to the console
window.LogLevel = LogLevel;

// Export the knowledge base logger to the console
window.KnowledgeBaseLogger = KnowledgeBaseLogger;

// Export the WebSocket logger to the console
window.WebSocketLogger = WebSocketLogger;
