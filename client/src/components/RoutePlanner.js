import React, { useRef } from 'react';
import Draggable from 'react-draggable';

const RoutePlanner = ({ onFindRoutes, onShowOptimal, routesFound, message, viewMode }) => {
    const nodeRef = useRef(null);

    return (
        // Dragging is now disabled when in dashboard mode
        <Draggable nodeRef={nodeRef} handle=".drag-handle" disabled={viewMode === 'dashboard'}>
            <div ref={nodeRef} className="route-planner">
                <h2 className="drag-handle">Demonstration Panel</h2>
                <p className="message">{message}</p>
                
                <button className="action-button" onClick={onFindRoutes} disabled={routesFound}>
                    1. Find All Routes
                </button>

                {routesFound && (
                    <button className="demo-button" onClick={onShowOptimal}>
                        2. Show Optimal Route
                    </button>
                )}
                
            </div>
        </Draggable>
    );
};

export default RoutePlanner;