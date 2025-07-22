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
 * 3D Avatar Component
 * 
 * This component renders a 3D avatar using Three.js and React Three Fiber.
 * It handles loading and displaying a GLB model with jaw bone animation
 * synchronized to audio playback.
 */

import React, { useEffect, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, useGLTF } from '@react-three/drei';
import * as THREE from 'three';

// Wave configurations for jaw movement animation
const wave1 = { frequency: 2.1, amplitude: 0.35 };  // Primary wave
const wave2 = { frequency: 3.3, amplitude: 0.15 };  // Secondary wave
const wave3 = { frequency: 5, amplitude: 0.2 };     // Tertiary wave

/**
 * 3D Model Component
 * Handles loading and animating the 3D avatar model
 * 
 * @param {Object} props Component properties
 * @param {string} props.glbUrl URL of the GLB model to load
 * @param {string} props.jawBoneName Name of the jaw bone in the model
 * @param {boolean} props.isTalking Whether the avatar should animate speech
 * @param {Function} props.setReady Callback when model is ready
 */
function Model({ glbUrl, jawBoneName, isTalking = false, setReady }) {
    const group = useRef();
    const { scene, animations } = useGLTF(glbUrl);
    const { camera } = useThree();
    const mixer = useRef();
    const jawBone = useRef();
    const timeRef = useRef(0);
    const [center, setCenter] = useState(new THREE.Vector3());

    useEffect(() => {
        // Center the model and configure camera
        const box = new THREE.Box3().setFromObject(scene);
        box.getCenter(center);
        center.setX(0.1);
        setCenter(center);

        // Configure materials and find jaw bone
        scene.traverse((child) => {
            if (child.isMesh) {
                child.castShadow = true;
            } else if (child.isBone && child.name === jawBoneName) {
                jawBone.current = child;
            }
        });

        // Set up animation mixer
        mixer.current = new THREE.AnimationMixer(scene);
        animations.forEach((clip) => {
            const action = mixer.current.clipAction(clip);
            action.loop = THREE.LoopRepeat;
            action.play();
        });

        // Create shadow-receiving plane
        const planeGeometry = new THREE.PlaneGeometry(20, 20);
        const shadowMaterial = new THREE.ShadowMaterial({ opacity: 0.1 });
        shadowMaterial.transparent = true;
        shadowMaterial.depthWrite = false;

        const shadowPlane = new THREE.Mesh(planeGeometry, shadowMaterial);
        shadowPlane.receiveShadow = true;
        shadowPlane.rotation.x = -Math.PI / 2;
        scene.add(shadowPlane);

        // Set up lighting
        // Fill light for softer shadows
        const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
        fillLight.position.set(5, 8, -5);
        scene.add(fillLight);

        // Main directional light with shadows
        const light = new THREE.DirectionalLight(0xffffff, 1);
        light.position.set(-5, 10, 5);
        light.castShadow = true;

        // Configure shadow quality
        light.shadow.mapSize.width = 2048 * 4;
        light.shadow.mapSize.height = 2048 * 4;
        light.shadow.camera.near = 0.1;
        light.shadow.camera.far = 50;
        light.shadow.camera.left = -10;
        light.shadow.camera.right = 10;
        light.shadow.camera.top = 10;
        light.shadow.camera.bottom = -10;
        light.shadow.bias = -0.000001;

        scene.add(light);

        console.log('Avatar model ready');
        setReady(true);
    }, []);

    useFrame((state, delta) => {
        // Keep camera focused on model
        camera.lookAt(center);
        mixer.current?.update(delta);

        // Update animation time
        timeRef.current += delta;

        // Generate jaw movement from combined sine waves
        const time = timeRef.current;
        const sin1 = wave1.amplitude * Math.sin(2 * Math.PI * wave1.frequency * time);
        const sin2 = wave2.amplitude * Math.sin(2 * Math.PI * wave2.frequency * time);
        const sin3 = wave3.amplitude * Math.sin(2 * Math.PI * wave3.frequency * time);

        // Normalize combined waves to [0,1] range
        const combinedWave = sin1 + sin2 + sin3;
        const maxAmplitude = wave1.amplitude + wave2.amplitude + wave3.amplitude;
        const mouthControl = (combinedWave / maxAmplitude + 1) / 2;

        // Animate jaw bone when talking
        if (isTalking && jawBone.current) {
            jawBone.current.position.x -= 1.5 * mouthControl;
        }
    });

    return <primitive ref={group} object={scene} />;
}

/**
 * Avatar Container Component
 * Wraps the 3D model in a Three.js canvas with proper configuration
 * 
 * @param {Object} props Component properties
 * @param {string} props.glbUrl URL of the GLB model to load
 * @param {string} props.jawBoneName Name of the jaw bone in the model
 * @param {boolean} props.isTalking Whether the avatar should animate speech
 */
export default function Avatar({ glbUrl, jawBoneName, isTalking }) {
    const [isReady, setReady] = useState(false);

    return (
        <div className='avatar-container'>
            <Canvas
                camera={{ position: [-1, 1, 3], fov: 35 }}
                gl={{
                    alpha: true,
                    shadowMap: {
                        enabled: true,
                        type: THREE.PCFSoftShadowMap
                    }
                }}
                shadows
            >
                <ambientLight />
                <Model
                    glbUrl={glbUrl}
                    jawBoneName={jawBoneName}
                    isTalking={isTalking}
                    setReady={setReady}
                />
            </Canvas>

            {/* Loading indicator */}
            {!isReady &&
                <div className='loading'>
                    <p>Loading...</p>
                </div>
            }
        </div>
    );
}
