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
 * Application Entry Point
 * 
 * This is the main entry point for the Virtual Banking Assistant frontend application.
 * It configures AWS Amplify authentication and renders the root App component.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import { Amplify } from 'aws-amplify';

// Import required styles
import '@aws-amplify/ui-react/styles.css';
import 'bootstrap/dist/css/bootstrap.min.css';
import './index.css';

// Import components and configuration
import App from './App';
import reportWebVitals from './reportWebVitals';
import { awsConfig } from './aws-exports';

// Configure AWS Amplify with authentication settings
Amplify.configure(awsConfig);

// Create root element and render application
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
    <React.StrictMode>
        <App />
    </React.StrictMode>
);

// Initialize performance monitoring
// Pass a function to log results (e.g., reportWebVitals(console.log))
// or send to an analytics endpoint: https://bit.ly/CRA-vitals
reportWebVitals();
