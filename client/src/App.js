// client/src/App.js
import React, { useState } from 'react';
import MapComponent from './components/MapComponent';
import RoutePlanner from './components/RoutePlanner';
import './App.css';

const hostelCoords = [72.5418, 23.0337]; // Lng, Lat
const airportCoords = [72.6275, 23.0772]; // Lng, Lat

function App() {
    const [routes, setRoutes] = useState([]);
    const [optimalRouteId, setOptimalRouteId] = useState(null);
    const [routesFound, setRoutesFound] = useState(false); // NEW: Tracks if we've found routes
    const [message, setMessage] = useState('Click the first button to begin.');

    // Step 1: Find all routes
    const findRoutes = async () => {
        setRoutes([]);
        setOptimalRouteId(null);
        setRoutesFound(false);
        setMessage('Searching for routes...');
        try {
            const response = await fetch('http://localhost:5000/api/route', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ start: hostelCoords, end: airportCoords })
            });
            if (!response.ok) throw new Error('Failed to fetch routes.');
            
            const fetchedRoutes = await response.json();
            setRoutes(fetchedRoutes);
            setRoutesFound(true);
            setMessage('Routes found! Now find the optimal one.');
        } catch (error) {
            console.error(error);
            setMessage('Error: Could not find routes.');
        }
    };

    // Step 2: Show the optimal route
    const showOptimal = () => {
        let minDensity = Infinity;
        let bestRouteId = null;

        const routesWithDensity = routes.map(route => {
            const densityScore = Math.floor(Math.random() * 80) + 10; // Your mock density
            if (densityScore < minDensity) {
                minDensity = densityScore;
                bestRouteId = route.id;
            }
            return { ...route, densityScore };
        });
        
        setRoutes(routesWithDensity); // Update routes with scores
        setOptimalRouteId(bestRouteId);
        setMessage(`Optimal route found with density score: ${minDensity}`);
    };
    
    return (
        <div className="App">
            <RoutePlanner
                onFindRoutes={findRoutes}
                onShowOptimal={showOptimal}
                routesFound={routesFound}
                message={message}
            />
            <MapComponent 
                routes={routes}
                optimalRouteId={optimalRouteId}
            />
        </div>
    );
}

export default App;