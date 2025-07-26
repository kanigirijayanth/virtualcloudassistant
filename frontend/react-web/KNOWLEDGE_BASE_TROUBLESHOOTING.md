# Knowledge Base Integration Troubleshooting Guide

This guide provides instructions for troubleshooting issues with the knowledge base integration in the Nova Sonic frontend application.

## Configuration

The knowledge base integration uses the Bedrock knowledge base with ID "CLRDOVZGIY". This ID is configured in the `aws-exports.js` file.

## Debugging Tools

The application includes built-in debugging tools to help troubleshoot knowledge base issues:

### Browser Console Debugging

1. Open your browser's developer tools (F12 or right-click and select "Inspect")
2. Go to the Console tab
3. Enable debug mode by typing:
   ```javascript
   window.enableDebug()
   ```
4. You can change the log level using:
   ```javascript
   window.setLogLevel(window.LogLevel.DEBUG)  // More detailed logs
   window.setLogLevel(window.LogLevel.TRACE)  // Most detailed logs
   ```

### Knowledge Base Specific Logging

The application logs detailed information about knowledge base queries and responses. Look for log entries with the `[KnowledgeBase]` prefix.

### WebSocket Communication Logging

WebSocket communication is logged with the `[WebSocket]` prefix. This can help identify issues with the communication between the frontend and backend.

## Common Issues and Solutions

### 1. Knowledge Base ID Mismatch

**Symptoms:** Knowledge base queries fail, with logs showing a mismatch between the configured knowledge base ID and the one used by the backend.

**Solution:** 
- Verify that the knowledge base ID in `aws-exports.js` matches the one expected by the backend.
- Check the backend logs to see which knowledge base ID it's using.

### 2. Response Format Issues

**Symptoms:** Knowledge base responses are received but not displayed correctly.

**Solution:**
- Check the browser console for errors in parsing the knowledge base response.
- Look for log entries showing the structure of the received response.
- The application now supports multiple response formats, including direct Bedrock responses.

### 3. WebSocket Connection Issues

**Symptoms:** Knowledge base queries are not being sent or responses are not being received.

**Solution:**
- Check the WebSocket connection status in the browser console.
- Verify that the WebSocket URL in `aws-exports.js` is correct.
- Look for WebSocket error messages in the console.

### 4. Backend Processing Issues

**Symptoms:** Knowledge base queries are sent but no responses are received.

**Solution:**
- Check the backend logs for errors in processing knowledge base queries.
- Verify that the backend has the correct permissions to access the Bedrock knowledge base.
- Check if the backend is correctly forwarding the knowledge base ID to Bedrock.

## Testing Knowledge Base Queries

You can use the provided test script to verify that the knowledge base is working correctly:

```bash
python3 test_knowledge_base_focused.py
```

This script makes a direct API call to the Bedrock knowledge base and displays the results.

## Reporting Issues

If you encounter issues that you cannot resolve, please provide the following information:

1. Browser console logs with debug mode enabled
2. The query that failed
3. Any error messages displayed in the UI or console
4. The results of running the test script
