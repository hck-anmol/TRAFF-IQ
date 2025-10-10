// client/src/components/RoutePlanner.js
import React from 'react';

const RoutePlanner = ({ onFindRoutes, onShowOptimal, routesFound, message }) => {
    return (
        <div className="route-planner">
            <h2>Traff-IQ Demo</h2>
            <p className="message">{message}</p>
            
            {/* Button 1: Always visible */}
            <button className="action-button" onClick={() => {
    console.log("Button 1: Find All Routes was clicked!"); // <-- ADD THIS
    onFindRoutes();
}}>
                1. Find All Routes (Hostel to Airport)
            </button>

            {/* Button 2: Only shows up after routes are found */}
            {routesFound && (
                <button className="demo-button" onClick={onShowOptimal}>
                    2. Show Optimal Route
                </button>
            )}
        </div>
    );
};

export default RoutePlanner;