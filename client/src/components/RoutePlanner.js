// client/src/components/RoutePlanner.js
import React, { useRef } from 'react';
import Draggable from 'react-draggable';

const RoutePlanner = ({ onBeginDemo, onFindRoutes, onShowOptimal, routesFound, message, panelState }) => {
    const nodeRef = useRef(null);

    return (
        <Draggable nodeRef={nodeRef} handle=".drag-handle" disabled={panelState === 'initial'}>
            {/* The className is now dynamic */}
            <div ref={nodeRef} className={`route-planner ${panelState}`}>
                <h2 className="drag-handle">Traff-IQ Demo 🚦</h2>
                <p className="message">{message}</p>

                {/* Show this button only in the initial, centered state */}
                {panelState === 'initial' && (
                    <button className="action-button initial-button" onClick={onBeginDemo}>
                        Begin Demo
                    </button>
                )}

                {/* Show these buttons only in the final, docked state */}
                {panelState === 'docked' && (
                    <>
                        <button className="action-button" onClick={onFindRoutes} disabled={routesFound}>
                            1. Find All Routes
                        </button>
                        {routesFound && (
                            <button className="demo-button" onClick={onShowOptimal}>
                                2. Show Optimal Route
                            </button>
                        )}
                    </>
                )}
            </div>
        </Draggable>
    );
};

export default RoutePlanner;