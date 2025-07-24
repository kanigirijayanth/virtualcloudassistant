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
 * Knowledge Base Result Component
 * 
 * This component displays knowledge base query results in a structured format.
 */

import React, { useState } from 'react';
import { Card, Accordion, Badge } from 'react-bootstrap';

/**
 * KnowledgeBaseResult Component
 * Displays knowledge base query results
 * 
 * @param {Object} props Component properties
 * @param {string} props.title Title of the knowledge base result
 * @param {Array|string} props.content Content of the knowledge base result
 * @param {string} props.source Source of the knowledge base result
 * @param {Object} props.metadata Metadata of the knowledge base result
 */
function KnowledgeBaseResult({ title, content, source, metadata }) {
    const [expanded, setExpanded] = useState(false);
    
    // Helper function to extract filename from S3 URI
    const getFilenameFromS3Uri = (uri) => {
        if (!uri) return 'Unknown';
        const parts = uri.split('/');
        return parts[parts.length - 1];
    };
    
    // Render content based on type
    const renderContent = () => {
        // If content is an array of results
        if (Array.isArray(content)) {
            return (
                <Accordion defaultActiveKey="0">
                    {content.map((item, index) => (
                        <Accordion.Item eventKey={index.toString()} key={index}>
                            <Accordion.Header>
                                {item.title || `Result ${index + 1}`}
                                {item.score && (
                                    <Badge bg="info" className="ms-2">
                                        Score: {Math.round(item.score * 100)}%
                                    </Badge>
                                )}
                            </Accordion.Header>
                            <Accordion.Body>
                                <div className="mb-2">{item.content}</div>
                                {item.source && (
                                    <div className="text-muted small">
                                        Source: {getFilenameFromS3Uri(item.source)}
                                    </div>
                                )}
                            </Accordion.Body>
                        </Accordion.Item>
                    ))}
                </Accordion>
            );
        }
        
        // If content is a string
        return <div className="kb-content">{content}</div>;
    };
    
    return (
        <Card className="mb-3 knowledge-base-result">
            <Card.Header className="d-flex justify-content-between align-items-center">
                <div>
                    <i className="bi bi-book me-2"></i>
                    {title}
                </div>
                <Badge bg="primary">Knowledge Base</Badge>
            </Card.Header>
            <Card.Body>
                {renderContent()}
                
                {source && (
                    <div className="text-muted small mt-2">
                        Source: {getFilenameFromS3Uri(source)}
                    </div>
                )}
                
                {metadata && Object.keys(metadata).length > 0 && (
                    <div className="mt-2">
                        <button 
                            className="btn btn-sm btn-outline-secondary"
                            onClick={() => setExpanded(!expanded)}
                        >
                            {expanded ? 'Hide Metadata' : 'Show Metadata'}
                        </button>
                        
                        {expanded && (
                            <div className="mt-2 p-2 bg-light rounded">
                                <pre className="mb-0 small">
                                    {JSON.stringify(metadata, null, 2)}
                                </pre>
                            </div>
                        )}
                    </div>
                )}
            </Card.Body>
        </Card>
    );
}

export default KnowledgeBaseResult;
